import os
import django
from decouple import config

# Add backend to sys.path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment for core imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.supabase_client import supabase

def test_supabase_integration():
    print("🚀 Starting Supabase Integration Test...")
    bucket_name = config("SUPABASE_BUCKET_NAME", default="RakshakBucket")
    
    try:
        # 1. List files
        print(f"📁 Listing files in bucket: {bucket_name}")
        res = supabase.storage.from_(bucket_name).list()
        print(f"✅ Found {len(res)} files.")

        # 2. Upload dummy file
        test_filename = "test_connection.txt"
        test_content = b"Supabase Connection Verified"
        print(f"📤 Uploading test file: {test_filename}")
        
        # Determine if file exists to overwrite or skip
        try:
            supabase.storage.from_(bucket_name).upload(
                path=test_filename,
                file=test_content,
                file_options={"content-type": "text/plain"}
            )
            print("✅ Upload successful.")
        except Exception as upload_err:
             if "already exists" in str(upload_err).lower():
                 print("ℹ️ File already exists, proceeding to URL check.")
             else:
                 raise upload_err

        # 3. Get Public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(test_filename)
        print(f"🔗 Public URL: {public_url}")

        # 4. Clean up
        print(f"🗑️ Deleting test file...")
        supabase.storage.from_(bucket_name).remove([test_filename])
        print("✅ Cleanup successful.")
        
        print("\n🏆 SUPABASE INTEGRATION IS READY!")

    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")

if __name__ == "__main__":
    test_supabase_integration()
