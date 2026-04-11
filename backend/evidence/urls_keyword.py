from django.urls import path
from .views import KeywordUploadView

urlpatterns = [
    path('upload/', KeywordUploadView.as_view(), name='keyword_upload'),
]
