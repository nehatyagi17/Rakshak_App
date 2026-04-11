from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class RakshakProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rakshak_profile')
    rakshak_id = models.CharField(max_length=15, unique=True, db_index=True)
    trust_score = models.IntegerField(default=50)
    face_signature_hash = models.TextField(blank=True, null=True)
    safety_keyword = models.CharField(max_length=50, default='emergency', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_trust_tier(self):
        """
        Calculates the 'Trust Tier' based on the trust_score.
        """
        if self.trust_score <= 50:
            return "Newbie"
        elif self.trust_score <= 80:
            return "Verified"
        else:
            return "Guardian"

    def __str__(self):
        return f"{self.user.username} - {self.rakshak_id}"
