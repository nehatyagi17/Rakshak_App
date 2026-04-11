import random
import string
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import RakshakProfile

def generate_rakshak_id():
    """
    Generates a unique, non-sequential 8-character alphanumeric RAKSHAK-ID.
    Format: RAK-XXXX-XXXX
    """
    chars = string.ascii_uppercase + string.digits
    while True:
        part1 = ''.join(random.choices(chars, k=4))
        part2 = ''.join(random.choices(chars, k=4))
        rid = f"RAK-{part1}-{part2}"
        if not RakshakProfile.objects.filter(rakshak_id=rid).exists():
            return rid

@receiver(post_save, sender=User)
def create_rakshak_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically generate a RakshakProfile when a User is created.
    """
    if created:
        rid = generate_rakshak_id()
        RakshakProfile.objects.create(
            user=instance,
            rakshak_id=rid,
            trust_score=50  # Default trust score
        )
        print(f"✅ RAKSHAK-ID Generated: {rid} for user {instance.username}")
