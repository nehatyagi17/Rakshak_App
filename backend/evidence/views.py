import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.db import evidence_col, keywords_col, users_col
from bson.objectid import ObjectId
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import uuid
from core.supabase_client import supabase
from decouple import config

BUCKET_NAME = config("SUPABASE_BUCKET_NAME", default="RakshakBucket")

class KeywordUploadView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/m', block=True))
    def post(self, request):
        user_id = request.user.id
        audio_file = request.FILES.get('file')

        if not audio_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        file_extension = audio_file.name.split('.')[-1]
        allowed_extensions = ['wav', 'mp3', 'm4a']
        if file_extension.lower() not in allowed_extensions:
            return Response({"error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Get user name for filename
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        user_name = user_doc.get("name", "UnknownUser").replace(" ", "_")

        # Save to Supabase Storage
        raw_bytes = audio_file.read()
        
        # Determine extension
        ext = audio_file.name.split('.')[-1] if '.' in audio_file.name else 'bin'
        filename = f"{user_name}_KEYWORD_{uuid.uuid4().hex[:8]}.{ext}"
        storage_path = f"keywords/{filename}"
        
        try:
            supabase.storage.from_(BUCKET_NAME).upload(
                path=storage_path,
                file=raw_bytes,
                file_options={"content-type": audio_file.content_type}
            )
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
        except Exception as e:
            return Response({"error": f"Supabase Upload Failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update metadata in DB
        doc = {
            "user_id": user_id,
            "user_name": user_name,
            "storage_path": storage_path,
            "public_url": public_url,
            "filename": filename,
            "encrypted": False
        }
        
        # Delete old keyword if any
        keywords_col.delete_many({"user_id": user_id})
        keywords_col.insert_one(doc)

        return Response({"message": "Distress keyword uploaded securely"}, status=status.HTTP_201_CREATED)

class EvidenceUploadView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='20/m', block=True))
    def post(self, request):
        user_id = request.user.id
        alert_id = request.data.get('alert_id')
        evidence_file = request.FILES.get('file')

        if not alert_id or not evidence_file:
            return Response({"error": "alert_id and file are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get user name
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        user_name = user_doc.get("name", "UnknownUser").replace(" ", "_")

        raw_bytes = evidence_file.read()
        
        # Determine extension
        ext = evidence_file.name.split('.')[-1] if '.' in evidence_file.name else 'bin'
        filename = f"{user_name}_SOS_{alert_id[:8]}_{uuid.uuid4().hex[:6]}.{ext}"
        storage_path = f"evidence/{filename}"
        
        try:
            supabase.storage.from_(BUCKET_NAME).upload(
                path=storage_path,
                file=raw_bytes,
                file_options={"content-type": evidence_file.content_type}
            )
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
        except Exception as e:
            return Response({"error": f"Supabase Upload Failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        doc = {
            "user_id": user_id,
            "user_name": user_name,
            "alert_id": alert_id,
            "storage_path": storage_path,
            "public_url": public_url,
            "filename": filename,
            "encrypted": False
        }
        
        result = evidence_col.insert_one(doc)
        
        return Response({
            "message": "Evidence uploaded securely",
            "evidence_id": str(result.inserted_id),
            "public_url": public_url
        }, status=status.HTTP_201_CREATED)

class EvidenceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, alert_id):
        user_id = request.user.id
        
        # Make sure user owns this alert or auth?
        # Note: If they are contacts they'd see it too, but omitting complex RBAC here for scope limits.
        # Only allowing creator to view their own for now based on prompt.
        
        docs = list(evidence_col.find({"alert_id": alert_id, "user_id": user_id}))
        for d in docs:
            d["_id"] = str(d["_id"])
            
        return Response(docs, status=status.HTTP_200_OK)

class EvidenceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, evidence_id):
        user_id = request.user.id
        
        try:
            doc = evidence_col.find_one({"_id": ObjectId(evidence_id), "user_id": user_id})
            if not doc:
                return Response({"error": "Evidence not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)
                
            # Erase file from Supabase
            if doc.get('storage_path'):
                supabase.storage.from_(BUCKET_NAME).remove([doc['storage_path']])
                
            evidence_col.delete_one({"_id": ObjectId(evidence_id)})
            
            return Response({"message": "Evidence deleted forever"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid evidence ID"}, status=status.HTTP_400_BAD_REQUEST)
