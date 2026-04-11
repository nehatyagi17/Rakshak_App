from django.urls import path
from .views import EvidenceUploadView, EvidenceDetailView, EvidenceListView

urlpatterns = [
    path('upload/', EvidenceUploadView.as_view(), name='evidence_upload'),
    path('<str:alert_id>/', EvidenceListView.as_view(), name='evidence_list'),
    path('delete/<str:evidence_id>/', EvidenceDetailView.as_view(), name='evidence_delete'),
]
