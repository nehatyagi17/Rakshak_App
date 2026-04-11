import logging
from django.conf import settings

logger = logging.getLogger('django')

def send_emergency_sms(phone_number, victim_name, link):
    """
    Simulates sending an emergency SMS to a trusted contact.
    In a production environment, this would integrate with Twilio or AWS SNS.
    """
    twilio_enabled = getattr(settings, 'TWILIO_ENABLED', False)
    
    if twilio_enabled:
        # Placeholder for real Twilio integration
        logger.info(f" [TWILIO-SMS] Sending actual SMS to {phone_number}...")
        try:
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # message = client.messages.create(
            #     body=f"🚨 RAKSHAK EMERGENCY: {victim_name} is in danger! Track them here: {link}",
            #     from_=settings.TWILIO_PHONE_FROM,
            #     to=phone_number
            # )
            pass
        except Exception as e:
            logger.error(f" [TWILIO-ERROR] Failed to send real SMS: {e}")
    else:
        # Simulated SMS logic (which is what we want for now)
        border = "="*50
        logger.warning(f"\n{border}")
        logger.warning(f" [SIMULATED SMS DISPATCH]")
        logger.warning(f" TO: {phone_number}")
        logger.warning(f" STATUS: URGENT")
        logger.warning(f" MESSAGE: 🚨 RAKSHAK EMERGENCY: {victim_name} is in danger! Track them here: {link}")
        logger.warning(f"{border}\n")
