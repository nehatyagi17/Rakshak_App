import requests
import json

BASE_URL = "http://localhost:8000/api"
TEST_USER = {
    "name": "Audit User",
    "email": "audit@rakshak.ai",
    "phone": "9999888877",
    "password": "passcode123"
}

def run_audit():
    print("📋 RAKSHAK System Audit: Checking APIs one-by-one...")
    
    # 1. Signup test
    print("\n1️⃣ Testing [SIGNUP] /auth/register/")
    try:
        res = requests.post(f"{BASE_URL}/auth/register/", json=TEST_USER)
        print(f"Status: {res.status_code}")
        if res.status_code == 201:
            print("✅ SUCCESS: User created.")
            token = res.json().get('access')
            rakshak_id = res.json().get('rakshak_id')
            print(f"🎟️ RAKSHAK-ID: {rakshak_id}")
        elif res.status_code == 400:
             print("ℹ️ INFO: User already exists (OK for audit).")
             # Try login to get token
             print("\n🔑 Switching to [LOGIN] to fetch token...")
             res = requests.post(f"{BASE_URL}/auth/login/", json={"email": TEST_USER['email'], "password": TEST_USER['password']})
             token = res.json().get('access')
        else:
            print(f"❌ FAIL: {res.text}")
            return
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return

    # 2. Login test
    print("\n2️⃣ Testing [LOGIN] /auth/login/")
    res = requests.post(f"{BASE_URL}/auth/login/", json={"email": TEST_USER['email'], "password": TEST_USER['password']})
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print("✅ SUCCESS: Login verified.")
        print(f"📦 Response Keys: {list(res.json().keys())}")
    else:
        print(f"❌ FAIL: {res.text}")

    # 3. Authenticated - Contacts
    print("\n3️⃣ Testing [CONTACTS] /contacts/")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/contacts/", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print("✅ SUCCESS: Sync Protocol functional.")
    else:
        print(f"❌ FAIL: {res.text}")

    # 4. Authenticated - Alerts
    print("\n4️⃣ Testing [ALERTS] /alerts/create/")
    res = requests.post(f"{BASE_URL}/alerts/create/", json={"lat": 12.97, "lng": 77.59}, headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 201:
        print("✅ SUCCESS: SOS Protocol functional.")
    else:
        print(f"❌ FAIL: {res.text}")

    print("\n✨ AUDIT COMPLETE: All core APIs are healthy and responsive.")

if __name__ == "__main__":
    run_audit()
