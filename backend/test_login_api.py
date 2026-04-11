import requests

# Configuration
API_BASE = "http://127.0.0.1:8000/api"

def test_login(email, password):
    print(f"🚀 Testing Login for user: {email}")
    payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login/", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    # Using the credentials from setup.md for testing
    test_login("user@rakshak.ai", "password123")
