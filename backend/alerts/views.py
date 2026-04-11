from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.db import alerts_col, users_col, contacts_col
from bson.objectid import ObjectId
from rest_framework.permissions import IsAuthenticated
from .haversine import get_nearby_alerts, get_nearby_users
from notifications.expo_push import send_expo_push
from notifications.email_service import send_emergency_email
from django.contrib.auth.models import User
from .models import Incident, EvidenceChunk, IncidentLocation
from users.models import RakshakProfile
from datetime import datetime
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncWebsocketConsumer
import json

from django.views.generic import TemplateView
from rest_framework import permissions
from rest_framework.parsers import MultiPartParser, FormParser

logger = logging.getLogger('django')

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # Support both custom PyMongo users (is_admin) and standard Django Admins (is_staff)
        return (
            getattr(user, 'is_admin', False) or 
            getattr(user, 'is_staff', False) or 
            getattr(user, 'is_superuser', False)
        )

class AuthorityDashboardView(TemplateView):
    template_name = 'alerts/authority_dashboard.html'

class AlertTriggerView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='10/m', block=True))
    def post(self, request):
        user_id = request.user.id
        data = request.data
        lat = data.get('lat')
        lng = data.get('lng')
        threat_level = data.get('threat_level', 'LOW')

        user_email = request.user.email
        user_doc = users_col.find_one({"email": user_email})
        mongo_user_id = str(user_doc.get("_id")) if user_doc else str(user_id)
        
        alert_doc = {
            "user_id": mongo_user_id,
            "status": "active",
            "lat": float(lat) if lat else 0.0,
            "lng": float(lng) if lng else 0.0,
            "threat_level": threat_level,
            "created_at": datetime.utcnow().isoformat(),
            "comm_notify_count": 0
        }
        
        result = alerts_col.insert_one(alert_doc)
        alert_id = str(result.inserted_id)
        
        logger.warning(f"SOS Triggered: Alert {alert_id} for user {user_id}")
        
        if user_doc and user_doc.get("expo_push_token"):
             send_expo_push(
                user_doc["expo_push_token"],
                "RAKSHAK: SOS Initialized",
                "Stay calm. We are monitoring your situation.",
                {"alert_id": alert_id, "type": "SILENT_CHECK"}
             )

        try:
            from django.contrib.auth.models import User as DjangoUser
            real_user = DjangoUser.objects.filter(email=user_email).first()
            if real_user:
                incident = Incident.objects.create(
                    victim=real_user, 
                    status='Active', 
                    victim_name=real_user.get_full_name() or real_user.username,
                    mongo_alert_id=alert_id # Critical Mapping
                )
                emergency_token = str(incident.emergency_token)
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "authority_group",
                    {
                        "type": "broadcast_event",
                        "payload": {
                            "type": "SOS_START",
                            "incident_id": incident.id,
                            "token": emergency_token,
                            "victim_name": incident.victim_name,
                            "lat": float(lat),
                            "lng": float(lng)
                        }
                    }
                )
                logger.info(f" RAKSHAK: Authority Notified of SOS START: {incident.id}")
            else:
                emergency_token = None
        except Exception as e:
            logger.error(f" Failed to initialize ORM Incident: {e}")
            emergency_token = None

        return Response({
            "message": "Alert triggered. Resolution window starts.",
            "alert_id": alert_id,
            "emergency_token": emergency_token
        }, status=status.HTTP_201_CREATED)

class AlertVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        django_user = request.user
        alert_id = request.data.get('alert_id')
        stage = request.data.get('stage', 'guardian')
        
        if not alert_id:
            return Response({"error": "alert_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        user_email = django_user.email
        user_doc = users_col.find_one({"email": user_email})
        mongo_user_id = str(user_doc.get("_id")) if user_doc else str(user_id)
            
        alert_doc = alerts_col.find_one({"_id": ObjectId(alert_id), "user_id": mongo_user_id})
        if not alert_doc:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if alert_doc.get("status") != "active":
            alerts_col.update_one({"_id": ObjectId(alert_id)}, {"$set": {"status": "active"}})
            logger.info(f"ALERT VERIFIED: Alert {alert_id} is now ACTIVE")
        
        from django.contrib.auth.models import User as DjangoUser
        real_user = DjangoUser.objects.filter(email=django_user.email).first()
        if not real_user:
             real_user = DjangoUser.objects.filter(is_superuser=True).first()
        
        try:
            incident = Incident.objects.filter(mongo_alert_id=alert_id, status='Active').last()
            if not incident:
                incident = Incident.objects.create(
                    victim=real_user, 
                    status='Active',
                    mongo_alert_id=alert_id
                )
                logger.info(f"NEW INCIDENT RECORD CREATED (ESCALATION): {incident.id}")
            else:
                logger.info(f"USING EXISTING INCIDENT RECORD: {incident.id}")
        except Exception as db_err:
            logger.error(f"Database Record Failure: {db_err}")
            return Response({"error": "Failed to manage incident record in SQLite."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        user_doc = users_col.find_one({"email": django_user.email})
        lat, lng = alert_doc.get("lat"), alert_doc.get("lng")
        map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        media_link = f"http://192.168.137.158:8000{incident.evidence_chunks.first().chunk_file.url}" if incident.evidence_chunks.exists() else None
        emergency_token = str(incident.emergency_token) # SCOPE FIX: Define here for dispatchers below

        if user_doc:
            if stage in ['all', 'guardian']:
                try:
                    contacts = user_doc.get("trust_contacts", [])
                    for c in contacts:
                        if c.get("email"):
                            send_emergency_email(c["email"], user_doc.get("name", "A Rakshak User"), map_link)
                            
                    contact_phones = [c["phone"] for c in contacts if c.get("phone")]
                    contact_users = users_col.find({"phone": {"$in": contact_phones}})
                    for contact_user in contact_users:
                        # Ensure we do not send the SOS to the person who triggered it
                        if str(contact_user.get("_id")) == str(user_doc.get("_id")):
                            continue
                            
                        if contact_user.get("expo_push_token"):
                            send_expo_push(
                                contact_user["expo_push_token"],
                                "🚨 EMERGENCY ALERT",
                                f"{user_doc.get('name')} is in danger! Location attached.",
                                {
                                    "alert_id": alert_id, 
                                    "type": "EMERGENCY",
                                    "lat": lat,
                                    "lng": lng,
                                    "map_link": map_link
                                }
                            )
                except Exception as g_err:
                    logger.error(f"Guardian Dispatch Error: {g_err}")

            if stage in ['all', 'community']:
                if lat and lng:
                    res = alerts_col.find_one_and_update(
                        {"_id": ObjectId(alert_id), "comm_notify_count": {"$lt": 2}},
                        {"$inc": {"comm_notify_count": 1}},
                        return_document=True
                    )
                    
                    if res:
                        try:
                            notify_count = res.get("comm_notify_count", 0)
                            nearby_users = get_nearby_users(lat, lng, radius_m=2000, exclude_user_id=user_id)
                            logger.info(f"Atomic Signal {notify_count}/2 Dispatched for Alert {alert_id}")
                            
                            channel_layer = get_channel_layer()
                            
                            for user_data in nearby_users:
                                u_id = str(user_data.get("_id"))
                                
                                # STRICT EXCLUSION: Do not send the rescue notification to the victim
                                if str(u_id) == str(user_doc.get("_id")):
                                    continue
                                    
                                if user_data.get("expo_push_token"):
                                    send_expo_push(user_data["expo_push_token"], "🚨 DISTRESS NEARBY", "Tap to help!", {
                                        "type": "NEARBY_SOS", 
                                        "alert_id": alert_id,
                                        "emergency_token": emergency_token,  # Critical Sync
                                        "lat": lat, 
                                        "lng": lng
                                    })
                                async_to_sync(channel_layer.group_send)(
                                    f"user_{u_id}",
                                    {
                                        "type": "emergency_alert",
                                        "alert_type": "EMERGENCY_ALERT",
                                        "alert_id": alert_id,
                                        "rakshak_id": user_doc.get("rakshak_id"),
                                        "name": user_doc.get("name"),
                                        "location": [lng, lat],
                                        "threat_level": "CRITICAL"
                                    }
                                )

                        except Exception as community_err:
                            logger.error(f"Community Dispatch Error: {community_err}")
                    else:
                        logger.info(f"Atomic Guard: Blocked redundant broadcast for {alert_id}")
        
        return Response({
            "message": "Alert verified and protocol active",
            "emergency_token": str(incident.emergency_token)
        }, status=status.HTTP_200_OK)

class VerifyHandshakeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('emergency_token')
        rescuer_rakshak_id = request.data.get('volunteer_rakshak_id')
        if not token or not rescuer_rakshak_id:
            return Response({"error": "Missing token or ID"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Expand to allow both Active and Verified (in case of double-ping)
            incident = Incident.objects.filter(emergency_token=token, status__in=['Active', 'Verified']).first()
        except Exception:
            return Response({"error": "Invalid token format"}, status=status.HTTP_400_BAD_REQUEST)
            
        if not incident:
            return Response({"error": "Valid incident with this token not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if incident.status == 'Verified':
             return Response({"message": "Handshake already verified.", "victim_name": incident.victim.username}, status=status.HTTP_200_OK)
        profile = RakshakProfile.objects.filter(rakshak_id=rescuer_rakshak_id).first()
        if not profile:
            return Response({"error": "Rescuer profile not found"}, status=status.HTTP_404_NOT_FOUND)
        incident.rescuer = profile.user
        incident.status = 'Verified'
        incident.verified_at = datetime.utcnow()
        incident.save()
        profile.trust_score += 5
        profile.save()
        
        logger.info(f"HANDSHAKE COMPLETE: Incident {incident.id} verified by {rescuer_rakshak_id}")
        
        try:
            victim_user = incident.victim
            victim_doc = users_col.find_one({"email": victim_user.email})
            if victim_doc:
                contacts = victim_doc.get("trust_contacts", [])
                for c in contacts:
                    if c.get("email"):
                        send_emergency_email(
                            c["email"], 
                            victim_doc.get("name", "Victim"), 
                            f"Help has arrived! The rescue is being handled by Verified Volunteer: {rescuer_rakshak_id}"
                        )
                    contact_user = users_col.find_one({"phone": c.get("phone")})
                    if contact_user and contact_user.get("expo_push_token"):
                        send_expo_push(
                            contact_user["expo_push_token"],
                            "RESCUE ARRIVED",
                            f"Help has arrived for {victim_doc.get('name')}. Rescuer: {rescuer_rakshak_id}",
                            {"type": "HELP_ARRIVED", "volunteer_id": rescuer_rakshak_id}
                        )
        except Exception as notify_err:
            logger.error(f"Handshake Notification Failure: {notify_err}")

        return Response({
            "message": "Handshake successful. Family notified.",
            "victim_name": incident.victim.username,
            "new_trust_score": profile.trust_score
        }, status=status.HTTP_200_OK)

class VerifyBiometricView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_email = request.user.email.strip().lower()
        current_vector = request.data.get('biometric_vector')
        
        if not current_vector or not isinstance(current_vector, list):
            return Response({"error": "Valid biometric vector required"}, status=status.HTTP_400_BAD_REQUEST)
            
        user_doc = users_col.find_one({"email": user_email})

        if not user_doc or "biometric_vector" not in user_doc:
            return Response({"error": "No enrolled biometric data found. Please enroll during signup."}, status=status.HTTP_401_UNAUTHORIZED)

            
        stored_vector = user_doc.get("biometric_vector")
        
        from .biometric_utils import cosine_similarity
        similarity = cosine_similarity(stored_vector, current_vector)
        
        logger.info(f"BIOMETRIC CHALLENGE: User {user_email} Similarity: {similarity:.4f}")
        
        if similarity >= 0.85:
            return Response({
                "verified": True,
                "similarity": similarity,
                "token": "BIO_AUTH_SUCCESS_" + str(int(datetime.utcnow().timestamp()))
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "verified": False,
                "similarity": similarity,
                "error": "Signature mismatch"
            }, status=status.HTTP_401_UNAUTHORIZED)

class AlertNearbyView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            lat = float(request.GET.get('lat'))
            lng = float(request.GET.get('lng'))
            radius = float(request.GET.get('radius_m', 1500))
        except (TypeError, ValueError):
            return Response({"error": "Invalid lat, lng, or radius"}, status=status.HTTP_400_BAD_REQUEST)
            
        user_email = request.user.email
        user_doc = users_col.find_one({"email": user_email})
        exclude_id = str(user_doc.get("_id")) if user_doc else str(request.user.id)
            
        nearby = get_nearby_alerts(lat, lng, radius, exclude_user_id=exclude_id)
        
        # Hydrate nearby alerts with emergency_tokens from Django Incident Model
        for alert in nearby:
            # FIX: MongoDB Hex IDs cannot be mapped to SQLite Integer IDs directly.
            # We now use the dedicated mongo_alert_id field.
            incident = Incident.objects.filter(mongo_alert_id=alert['alert_id']).first() 
            if not incident:
                # Try fallback by alert_id stored in metadata if available
                incident = Incident.objects.filter(emergency_token=alert.get('token')).first()
            
            if incident:
                alert['emergency_token'] = str(incident.emergency_token)
            else:
                alert['emergency_token'] = None

        return Response(nearby, status=status.HTTP_200_OK)

class UploadEvidenceChunkView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        token = request.data.get('emergency_token')
        if not token or token == "":
            return Response({"error": "emergency_token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        sequence = request.data.get('sequence', 0)
        file_obj = request.FILES.get('file')
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        remote_url = request.data.get('remote_url')  # New: Supabase URL from app

        # Accept chunks for both Active and Verified (handover phase)
        try:
            incident = Incident.objects.filter(emergency_token=token, status__in=['Active', 'Verified']).first()
        except (ValueError, Exception):
            return Response({"error": "Invalid emergency token format"}, status=status.HTTP_400_BAD_REQUEST)
            
        if not incident:
            logger.warning(f" [UPLOAD-CHUNK] 404: Incident not found for token {token} (sequence: {sequence})")
            return Response({"error": "Incident not found or resolved"}, status=status.HTTP_404_NOT_FOUND)

        # 1. Save locally only if a file was actually provided
        chunk_local_url = None
        if file_obj:
            chunk = EvidenceChunk.objects.create(
                incident=incident,
                chunk_file=file_obj,
                sequence_number=sequence
            )
            chunk_local_url = chunk.chunk_file.url

        # 2. Update Location Tracking
        if lat and lng:
            # Update SQLite History
            IncidentLocation.objects.create(incident=incident, lat=lat, lng=lng)
            
            # Update Primary Incident Record
            incident.last_lat = float(lat)
            incident.last_lng = float(lng)
            incident.save()
            
            # Sync to MongoDB (for Polling Dashboard)
            if incident.mongo_alert_id:
                from core.db import alerts_col
                from bson.objectid import ObjectId
                alerts_col.update_one(
                    {"_id": ObjectId(incident.mongo_alert_id)},
                    {"$set": {"lat": float(lat), "lng": float(lng)}}
                )

        # 3. Broadcast to Dashboard (Prioritize the remote_url if provided)
        # Using Supabase URL for dashboard playback
        final_video_url = remote_url or (chunk_local_url if chunk_local_url else None)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "authority_group",
            {
                "type": "broadcast_event",
                "payload": {
                    "type": "NEW_CHUNK",
                    "incident_id": incident.id,
                    "chunk_url": final_video_url,
                    "sequence": sequence,
                    "lat": float(lat) if lat else None,
                    "lng": float(lng) if lng else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

        return Response({"status": "Pulse Received", "video_synced": bool(final_video_url)}, status=status.HTTP_200_OK)

class AlertResolveView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, alert_id):
        user_id = request.user.id
        user_email = request.user.email
        user_doc = users_col.find_one({"email": user_email})
        mongo_user_id = str(user_doc.get("_id")) if user_doc else str(user_id)
        
        result = alerts_col.update_one(
            {"_id": ObjectId(alert_id), "user_id": mongo_user_id},
            {"$set": {"status": "resolved", "resolved_at": datetime.utcnow().isoformat()}}
        )
        if result.modified_count == 0:
            return Response({"error": "Alert not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Alert resolved successfully"}, status=status.HTTP_200_OK)

class AdminAlertListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request):
        active_alerts = list(alerts_col.find({"status": "active"}).sort("created_at", -1))
        for alert in active_alerts:
            alert["_id"] = str(alert["_id"])
            
            # Hydrate with Latest Tracking Data from SQLite if available
            incident = Incident.objects.filter(mongo_alert_id=alert["_id"]).first()
            if incident:
                alert["lat"] = incident.last_lat or alert["lat"]
                alert["lng"] = incident.last_lng or alert["lng"]
            
            # Robust User Lookup (Handles both MongoDB ObjectId and legacy/Django integer IDs)
            user_id_raw = alert.get("user_id")
            user_doc = None
            if user_id_raw:
                try:
                    if isinstance(user_id_raw, str) and len(user_id_raw) == 24:
                        user_doc = users_col.find_one({"_id": ObjectId(user_id_raw)})
                    else:
                        # Try integer lookup (Django compatibility)
                        user_doc = users_col.find_one({"_id": int(user_id_raw)})
                except (Exception, ValueError):
                    pass
            
            alert["user_name"] = user_doc.get("name", "Unknown User") if user_doc else "Unknown User"
            
            # Fetch Latest Video Chunk (for Polling/Fallback)
            from .models import EvidenceChunk
            latest_chunk = EvidenceChunk.objects.filter(incident=incident).order_by('-timestamp').first()
            alert["latest_chunk_url"] = latest_chunk.chunk_file.url if latest_chunk else None
            
        return Response(active_alerts, status=status.HTTP_200_OK)

class AdminDashboardView(TemplateView):
    template_name = "alerts/dashboard.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_active"] = alerts_col.count_documents({"status": "active"})
        return context
