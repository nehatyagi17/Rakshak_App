import google.generativeai as genai
from decouple import config
import json
import logging
import base64
import requests
from io import BytesIO

logger = logging.getLogger('django')

# Configure Gemini
genai.configure(api_key=config('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

def verify_face_with_gemini(reference_url, live_image_b64):
    """
    Compares a stored reference image (URL) with a live selfie (Base64)
    using Gemini 1.5 Flash.
    """
    try:
        # Load Reference Image from Supabase URL
        resp = requests.get(reference_url)
        if resp.status_code != 200:
            return {"match": False, "confidence": 0, "analysis": "Could not fetch reference image from Supabase."}
        
        ref_image_data = resp.content
        
        # Prepare Live Image
        # If live_image_b64 is a data URL (e.g. data:image/jpeg;base64,...), strip the prefix
        if "," in live_image_b64:
            live_image_b64 = live_image_b64.split(",")[1]
        
        live_image_data = base64.b64decode(live_image_b64)

        # System Instruction for Gemini
        prompt = """
        Compare these two images. 
        Image 1 (Reference) is the registered owner. 
        Image 2 (Live Selfie) is a person trying to stop an emergency alert. 
        
        Task:
        1. Determine if they are the same individual. Focus on facial structure, not lighting or hair.
        2. Detect if Image 2 is a 'spoof' (e.g., a photo of a photo, a mask, or a digital screen).
        
        Return ONLY a JSON object:
        {
          "match": boolean, 
          "confidence": float (0.0 to 1.0), 
          "analysis": "Brief explanation of the decision"
        }
        """

        # Call Gemini Vision
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": ref_image_data},
            {"mime_type": "image/jpeg", "data": live_image_data}
        ])

        # Parse JSON response
        try:
            # Strip markdown snippets if Gemini wraps it in ```json ... ```
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean_text)
            return result
        except Exception as parse_err:
            logger.error(f"Failed to parse Gemini JSON: {response.text}")
            return {"match": False, "confidence": 0, "analysis": f"AI Parsing failed: {str(parse_err)}"}

    except Exception as e:
        logger.error(f"Gemini Face Verification Error: {str(e)}")
        return {"match": False, "confidence": 0, "analysis": f"System Error: {str(e)}"}
