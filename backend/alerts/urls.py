from django.urls import path
from . import views
from .views import (
    AlertTriggerView, AlertVerifyView, AlertNearbyView, 
    AlertResolveView, AdminAlertListView, AdminDashboardView, 
    VerifyHandshakeView, VerifyBiometricView
)


urlpatterns = [
    path('trigger/', AlertTriggerView.as_view(), name='alert_trigger'),
    path('verify/', AlertVerifyView.as_view(), name='alert_verify'),
    path('verify-biometric/', VerifyBiometricView.as_view(), name='verify_biometric'),
    path('nearby/', AlertNearbyView.as_view(), name='alert_nearby'),
    path('upload/', views.UploadEvidenceChunkView.as_view(), name='alert_upload_legacy'),
    path('upload-chunk/', views.UploadEvidenceChunkView.as_view(), name='alert_upload_chunk'),
    path('authority/dashboard/', views.AuthorityDashboardView.as_view(), name='authority_dashboard'),

    path('verify-handshake/', VerifyHandshakeView.as_view(), name='verify_handshake'),
    path('<str:alert_id>/resolve/', AlertResolveView.as_view(), name='alert_resolve'),
    # Admin Dashboard (Desktop)
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/list/', AdminAlertListView.as_view(), name='admin_list'),
]
