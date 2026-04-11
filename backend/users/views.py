from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken
import bcrypt
from core.db import users_col
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .models import RakshakProfile
import logging
from datetime import datetime
from bson.objectid import ObjectId
import speech_recognition as sr
import io
import imageio_ffmpeg
import subprocess

logger = logging.getLogger('django')

class RegisterView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        data = request.data
        email = data.get('email', '').strip().lower()
        phone = data.get('phone')
        password = data.get('password')
        name = data.get('name')

        if not all([email, phone, password, name]):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        # Check existing
        if users_col.find_one({"$or": [{"email": email}, {"phone": phone}]}):
            return Response({"error": "User with this email or phone already exists"}, status=status.HTTP_400_BAD_REQUEST)

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user_doc = {
            "email": email,
            "phone": phone,
            "password": hashed,
            "name": name,
            "biometric_vector": data.get('biometric_vector'), # 128-dim Faceprint
            "safety_keyword": data.get('safety_keyword', 'emergency'),
            "expo_push_token": None,
            "location": None
        }

        
        result = users_col.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # --- NEW SHADOW USER & PROFILE INTEGRATION ---
        # Create a Django User and ensure RakshakProfile exists
        try:
            django_user, created = User.objects.get_or_create(username=email, email=email)
            if created:
                django_user.set_password(password)
                django_user.save()
            
            # --- DEFENSIVE: Ensure profile exists even if user was previously created ---
            from .signals import generate_rakshak_id
            profile, p_created = RakshakProfile.objects.get_or_create(user=django_user)
            if p_created or not profile.rakshak_id:
                profile.rakshak_id = generate_rakshak_id()
            
            # Sync safety_keyword
            if data.get('safety_keyword'):
                profile.safety_keyword = data.get('safety_keyword')
            
            profile.save()
                
            rakshak_id = profile.rakshak_id
            users_col.update_one({"_id": ObjectId(user_id)}, {"$set": {"rakshak_id": rakshak_id}})
        except Exception as e:
            logger.error(f"❌ Shadow User/Profile Sync Error: {e}")
            return Response({"error": "Identity synchronization failed. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        refresh = RefreshToken.for_user(django_user)
        refresh['user_id'] = user_id
        
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user_id,
            "rakshak_id": rakshak_id,
            "biometric_vector": user_doc.get("biometric_vector")
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = []
    authentication_classes = []

    @method_decorator(ratelimit(key='ip', rate='5/m', block=True))
    def post(self, request):
        data = request.data
        email = data.get('email', '').strip().lower()
        password = data.get('password')

        if not email or not password:
            return Response({"error": "Missing email or password"}, status=status.HTTP_400_BAD_REQUEST)

        user_doc = users_col.find_one({"email": email})
        if not user_doc:
            logger.warning(f"❌ Login Failure: User not found with email '{email}'")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not bcrypt.checkpw(password.encode('utf-8'), user_doc['password'].encode('utf-8')):
            logger.warning(f"❌ Login Failure: Password mismatch for user '{email}'")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
        # --- SYSTEM SELF-HEALING: Ensure Django User exists for JWT ---
        django_user, created = User.objects.get_or_create(email=email, defaults={'username': email})
        if not created:
            django_user.set_password(password)
            django_user.save()
            
        # Ensure RakshakProfile exists for handshakes
        from .signals import generate_rakshak_id
        rakshak_profile, p_created = RakshakProfile.objects.get_or_create(user=django_user)
        if p_created or not rakshak_profile.rakshak_id:
            rakshak_profile.rakshak_id = generate_rakshak_id()
            rakshak_profile.save()
            
        rakshak_id = rakshak_profile.rakshak_id
        user_id = str(user_doc["_id"])
        
        refresh = RefreshToken.for_user(django_user)
        # --- FIX: Manually inject MongoDB ID into token claims for PyMongoJWTAuthentication ---
        refresh['user_id'] = user_id

        
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user_id,
            "rakshak_id": rakshak_id,
            "biometric_enrolled": bool(user_doc.get("biometric_vector")),
            "biometric_vector": user_doc.get("biometric_vector")
        }, status=status.HTTP_200_OK)



class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = request.user.email.strip().lower()
        user_doc = users_col.find_one({"email": user_email}, {"password": 0})
        if not user_doc:
            return Response({"error": "User not found in custom database"}, status=status.HTTP_404_NOT_FOUND)
            
        user_doc["_id"] = str(user_doc["_id"])
        
        # Ensure safety_keyword is present even if not in MongoDB
        if "safety_keyword" not in user_doc:
            try:
                django_user = User.objects.get(email=user_email)
                profile = django_user.rakshak_profile
                user_doc["safety_keyword"] = profile.safety_keyword or "emergency"
            except Exception:
                user_doc["safety_keyword"] = "emergency"
                
        return Response(user_doc, status=status.HTTP_200_OK)
        
    def put(self, request):
        user_email = request.user.email.strip().lower()
        data = request.data
        update_fields = {}
        
        if 'name' in data: update_fields['name'] = data['name']
        if 'phone' in data: update_fields['phone'] = data['phone']
        if 'expo_push_token' in data: update_fields['expo_push_token'] = data['expo_push_token']
        if 'location' in data: update_fields['location'] = data['location']
        if 'biometric_vector' in data: update_fields['biometric_vector'] = data['biometric_vector']
        if 'safety_keyword' in data: update_fields['safety_keyword'] = data['safety_keyword']
        
        if not update_fields:
            return Response({"error": "No update fields provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        result = users_col.update_one({"email": user_email}, {"$set": update_fields})
        if result.matched_count == 0:
            return Response({"error": "Failed to locate user identity record"}, status=status.HTTP_404_NOT_FOUND)
            
        # Sync safety_keyword to Django Profile if updated
        if 'safety_keyword' in update_fields:
            try:
                django_user = User.objects.get(email=user_email)
                profile = django_user.rakshak_profile
                profile.safety_keyword = update_fields['safety_keyword']
                profile.save()
            except Exception as e:
                logger.error(f"Sync error for safety_keyword: {e}")
            
        return Response({"message": "Profile updated successfully"}, status=status.HTTP_200_OK)


class UpdateLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        lat = request.data.get('lat')
        lng = request.data.get('lng')

        if lat is None or lng is None:
            return Response({"error": "lat and lng are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Update MongoDB users collection with the new location as GeoJSON
        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"location": {"type": "Point", "coordinates": [float(lng), float(lat)]}, "last_seen": datetime.utcnow().isoformat()}}
        )

        return Response({"message": "Location synchronized"}, status=status.HTTP_200_OK)


class VoiceAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({"error": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Get user's safety keyword from Django profile
        try:
            user_email = request.user.email
            django_user = User.objects.get(email=user_email)
            profile = django_user.rakshak_profile
            safety_keyword = (profile.safety_keyword or "emergency").lower().strip()
        except Exception:
            safety_keyword = "emergency"

        r = sr.Recognizer()
        r.energy_threshold = 300 # Prevent background hum triggers
        
        try:
            # --- CONVERSION (Subprocess to bypass missing ffprobe) ---
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            raw_audio = audio_file.read()
            process = subprocess.Popen(
                [ffmpeg_path, '-i', 'pipe:0', '-f', 'wav', 'pipe:1'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            wav_data, err = process.communicate(input=raw_audio)
            
            if process.returncode != 0:
                logger.error(f"FFmpeg conversion failed: {err.decode('utf-8', errors='ignore')}")
                return Response({"error": "Audio conversion failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            wav_io = io.BytesIO(wav_data)

            with sr.AudioFile(wav_io) as source:
                # Optimized calibrate for short chunks
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = r.record(source)
            
            import string
            from difflib import SequenceMatcher

            def similarity(a, b):
                return SequenceMatcher(None, a, b).ratio()

            # Use Google Speech Recognition (requires internet)
            detected_phrase = r.recognize_google(audio_data, language="en-in").lower().strip()
            
            # --- PERFECTED SOS LOGIC (USER SUGGESTED) ---
            clean_detected = detected_phrase.translate(str.maketrans('', '', string.punctuation))
            clean_keyword = safety_keyword.translate(str.maketrans('', '', string.punctuation))
            
            DISTRESS_TERMS = ["help", "bachao", "emergency", "danger", "save me", "police"]
            active_keywords = [clean_keyword] + DISTRESS_TERMS
            
            is_triggered = False
            max_fuzzy_score = 0
            match_type = "None"

            # 1. Exact Substring Match
            for kw in active_keywords:
                if kw in clean_detected:
                    is_triggered = True
                    match_type = "Direct"
                    break
            
            # 2. Fuzzy Matching Engine (Checks if any word sounds like active keywords)
            if not is_triggered:
                detected_words = clean_detected.split()
                for word in detected_words:
                    for kw in active_keywords:
                        score = similarity(kw, word)
                        if score > max_fuzzy_score:
                            max_fuzzy_score = score
                        if score > 0.8: # User's specified threshold
                            is_triggered = True
                            match_type = "Fuzzy"
                            break
                    if is_triggered:
                        break
            
            logger.info(f"Voice SOS Analysis: Detected='{detected_phrase}', Triggered={is_triggered} (Type: {match_type})")

            return Response({
                "status": "EMERGENCY_TRIGGERED" if is_triggered else "SECURE",
                "user_keyword": safety_keyword,
                "detected_phrase": detected_phrase,
                "confidence_score": round(max(0.95 if is_triggered and match_type == "Direct" else max_fuzzy_score, 0), 2),
                "match_type": match_type
            }, status=status.HTTP_200_OK)

        except sr.UnknownValueError:
            return Response({"status": "SECURE", "detected_phrase": "[Inaudible]", "error": "Could not understand audio"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Voice Analysis Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoiceEnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({"error": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

        r = sr.Recognizer()
        r.energy_threshold = 300
        
        try:
            # --- CONVERSION ---
            import subprocess
            import imageio_ffmpeg
            import io
            import string
            from django.contrib.auth.models import User
            
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            raw_audio = audio_file.read()
            process = subprocess.Popen(
                [ffmpeg_path, '-i', 'pipe:0', '-f', 'wav', 'pipe:1'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            wav_data, err = process.communicate(input=raw_audio)
            
            if process.returncode != 0:
                return Response({"error": "Audio conversion failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            wav_io = io.BytesIO(wav_data)

            with sr.AudioFile(wav_io) as source:
                # Use 0.5s for enrollment to allow user to stabilize
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = r.record(source)
            
            # Transcription (Perfected logic)
            detected_phrase = r.recognize_google(audio_data, language="en-in").lower().strip()
            clean_phrase = detected_phrase.translate(str.maketrans('', '', string.punctuation))
            
            new_keyword = clean_phrase
            
            # Update Profile
            user_email = request.user.email
            django_user = User.objects.get(email=user_email)
            profile = django_user.rakshak_profile
            profile.safety_keyword = new_keyword
            profile.save()
            
            logger.info(f"✅ RAKSHAK: Voice Enrollment Success - Keyword Armed: '{new_keyword}'")
                
            return Response({
                "message": "Keyword registered successfully", 
                "keyword": new_keyword,
                "status": "ARMED"
            }, status=status.HTTP_200_OK)

        except sr.UnknownValueError:
            return Response({"error": "Could not understand audio. Please speak clearly."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Enrollment Analysis Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
