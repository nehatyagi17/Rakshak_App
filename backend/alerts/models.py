from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.

class Incident(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Verified', 'Verified'),
        ('Resolved', 'Resolved'),
    ]

    victim = models.ForeignKey(User, on_delete=models.CASCADE, related_name='victim_incidents')
    rescuer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rescuer_handshakes')
    mongo_alert_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    emergency_token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    victim_name = models.CharField(max_length=100, blank=True, null=True)
    last_lat = models.FloatField(null=True, blank=True)
    last_lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Incident {self.id} - {self.status}"

class EvidenceChunk(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='evidence_chunks')
    chunk_file = models.FileField(upload_to='evidence/chunks/')
    sequence_number = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_number']

class IncidentLocation(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='location_history')
    lat = models.FloatField()
    lng = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
