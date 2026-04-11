from django.urls import path
from .views import ProfileView, UpdateLocationView, VoiceAnalysisView, VoiceEnrollView

urlpatterns = [
    path('', ProfileView.as_view(), name='profile_detail'),
    path('update/', ProfileView.as_view(), name='profile_update'),
    path('update-location/', UpdateLocationView.as_view(), name='profile_location_sync'),
    path('voice-analysis/', VoiceAnalysisView.as_view(), name='voice_analysis'),
    path('voice-enroll/', VoiceEnrollView.as_view(), name='voice_enroll'),
]
