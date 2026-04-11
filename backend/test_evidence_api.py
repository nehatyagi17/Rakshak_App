import requests
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000/api"
TEST_USER = {"email": "user@rakshak.ai", "password": "password123"}
# A local image to upload
IMAGE_PATH = r"C:\Users\ayush\.gemini\antigravity\brain\339cf4c1-4bc1-4154-b4d1-970dc5373b75\megumin_kabuma_konosuba_1775227363883.png"

def verify_api_integration():
    print("🚀 Starting Live API Integration Test...")

    # 1. Login to get JWT Token
    print("🔑 Authenticating...")
    try:
        login_res = requests.post(f"{BASE_URL}/auth/login/", json=TEST_USER)
        if login_res.status_code != 200:
            print(f"❌ Login Failed: {login_res.text}")
            return
        token = login_res.json().get('access')
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Authenticated.")
    except Exception as e:
        print(f"❌ Connection Error during login: {e}")
        return

    # 2. Upload Evidence via API
    print("📤 Uploading image through API endpoint...")
    alert_id = "TEST_API_ALERT_123"
    
    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'file': ('megumin_api_test.png', f, 'image/png')}
            data = {'alert_id': alert_id}
            
            response = requests.post(
                f"{BASE_URL}/evidence/upload/", 
                headers=headers, 
                data=data, 
                files=files
            )

        print(f"📡 API Status: {response.status_code}")
        if response.status_code == 201:
            print("✅ SUCCESS: API accepted the upload and stored it in Supabase.")
            
            # 3. Verify public access via GET list
            print("🔍 Verifying retrieval...")
            list_res = requests.get(f"{BASE_URL}/evidence/{alert_id}/", headers=headers)
            evidence_list = list_res.json()
            
            if evidence_list:
                # Find the one we just uploaded
                match = next((item for item in evidence_list if item["filename"].startswith("Test_User_SOS")), None)
                if not match: match = evidence_list[-1] # Fallback to latest
                
                public_url = match.get('public_url')
                print(f"🔗 Public Supabase URL retrieved from API: {public_url}")
            else:
                print("❌ Failure: Evidence was stored but not found in list.")
        else:
            print(f"❌ API Error: {response.text}")
    except Exception as e:
        print(f"❌ Connection Error during upload: {e}")

if __name__ == "__main__":
    verify_api_integration()
