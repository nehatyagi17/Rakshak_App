import requests
import uuid

# Configuration
API_BASE = "http://127.0.0.1:8000/api"
UNIQUE_ID = uuid.uuid4().hex[:6]

def test_signup():
    print(f"🚀 Testing Signup for user: test_{UNIQUE_ID}@rakshak.ai")
    payload = {
        "name": f"Test User {UNIQUE_ID}",
        "email": f"test_{UNIQUE_ID}@rakshak.ai",
        "phone": f"99887766{UNIQUE_ID[-2:]}",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/register/", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_signup()
