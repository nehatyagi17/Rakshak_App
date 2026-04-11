import requests
import json

BASE_URL = 'http://127.0.0.1:8000/api'
creds = {'email': 'admin@rakshak.system', 'password': 'admin123'}

def verify_tracking():
    print("--- 1. Logging In ---")
    login_res = requests.post(f"{BASE_URL}/auth/login/", json=creds)
    token = login_res.json()['access']
    headers = {'Authorization': f'Bearer {token}'}

    print("--- 2. Triggering SOS (Initial Location: 10.0, 70.0) ---")
    trigger_res = requests.post(f"{BASE_URL}/alerts/trigger/", 
                               json={'lat': 10.0, 'lng': 70.0, 'threat_level': 'HIGH'}, 
                               headers=headers)
    alert_id = trigger_res.json()['alert_id']
    e_token = trigger_res.json()['emergency_token']
    print(f"Alert ID: {alert_id}, SOS Token: {e_token}")

    print("--- 3. Checking Admin List (Initial) ---")
    # Verify status is active (we might need to verify it first if the list only pulls active)
    # Let's verify it manually
    requests.post(f"{BASE_URL}/alerts/verify/", json={'alert_id': alert_id, 'stage': 'all'}, headers=headers)
    
    list_res = requests.get(f"{BASE_URL}/alerts/admin/list/", headers=headers).json()
    alert = next(a for a in list_res if a['_id'] == alert_id)
    print(f"Initial Dashboard Location: {alert['lat']}, {alert['lng']}")

    print("--- 4. Uploading Movement Chunk (New Location: 10.5, 70.5) ---")
    requests.post(f"{BASE_URL}/alerts/upload-chunk/", 
                 data={'emergency_token': e_token, 'sequence': 1, 'lat': 10.5, 'lng': 70.5}, 
                 headers=headers)

    print("--- 5. Checking Admin List (Updated) ---")
    list_res_new = requests.get(f"{BASE_URL}/alerts/admin/list/", headers=headers).json()
    alert_new = next(a for a in list_res_new if a['_id'] == alert_id)
    print(f"Updated Dashboard Location: {alert_new['lat']}, {alert_new['lng']}")

    if alert_new['lat'] == 10.5 and alert_new['lng'] == 70.5:
        print("\n✅ SUCCESS: Location Tracking is Synchronized!")
    else:
        print("\n❌ FAILURE: Location didn't update.")

if __name__ == '__main__':
    verify_tracking()
