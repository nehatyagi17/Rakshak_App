import os
import sys
from core.supabase_client import supabase
from decouple import config

# Setup environment variables for Django setup if needed, but not strictly for this script
bucket = config('SUPABASE_BUCKET_NAME', default='RakshakBucket')
path = r'C:\Users\ayush\.gemini\antigravity\brain\339cf4c1-4bc1-4154-b4d1-970dc5373b75\megumin_kabuma_konosuba_1775227363883.png'

try:
    with open(path, 'rb') as f:
        file_content = f.read()
        print(f"📤 Uploading image ({len(file_content)} bytes) to bucket '{bucket}'...")
        res = supabase.storage.from_(bucket).upload(
            path='megumin_konosuba.png', 
            file=file_content, 
            file_options={'content-type': 'image/png'}
        )
        url = supabase.storage.from_(bucket).get_public_url('megumin_konosuba.png')
        print(f"✅ Success! URL: {url}")
except Exception as e:
    # If already exists, just get URL
    if "already exists" in str(e).lower():
         url = supabase.storage.from_(bucket).get_public_url('megumin_konosuba.png')
         print(f"✅ Already exists. URL: {url}")
    else:
        print(f"❌ Error: {e}")
