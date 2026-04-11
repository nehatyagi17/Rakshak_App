import requests
from decouple import config
import logging

logger = logging.getLogger('django')

def send_expo_push(expo_token, title, body, data=None):
    if not data: data = {}
    url = config("EXPO_PUSH_URL", default="https://exp.host/--/api/v2/push/send")
    
    payload = {
        "to": expo_token,
        "title": title,
        "body": body,
        "data": data,
        "sound": "default",
        "priority": "high"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Failed to send Expo Push Notification to {expo_token}: {str(e)}")
        return False
