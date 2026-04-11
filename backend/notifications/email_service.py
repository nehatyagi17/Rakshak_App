import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_emergency_email(recipient_email, victim_name, map_link):
    """
    Asynchronously (simulated via non-blocking call) sends an emergency 
    email to the trusted guardian.
    """
    subject = f"🚨 URGENT: RAKSHAK Emergency Alert for {victim_name}"
    message = (
        f"This is an automated emergency alert from the RAKSHAK AI Safety System.\n\n"
        f"{victim_name} is in immediate distress and requires your help.\n\n"
        f"Live GPS Tracking: {map_link}\n\n"
        f"Encrypted audio and video evidence is being recorded and uploaded "
        f"to the Rakshak secure cloud on the victim's device.\n\n"
        f"Please act immediately and contact local emergency services if necessary."
    )
    
    try:
        # We default to fail_silently=False to ensure we catch config issues
        # in development.
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'alerts@rakshak.ai',
            [recipient_email],
            fail_silently=False,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to send emergency email: {str(e)}")
        return False
