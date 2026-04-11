import requests
import json
import io

BASE_URL = 'http://127.0.0.1:8000/api'
creds = {'email': 'admin@rakshak.system', 'password': 'admin123'}

def verify_handshake():
    print("--- 1. Logging In ---")
    login_res = requests.post(f"{BASE_URL}/auth/login/", json=creds)
    token = login_res.json()['access']
    headers = {'Authorization': f'Bearer {token}'}

    print("--- 2. Triggering SOS ---")
    trigger_res = requests.post(f"{BASE_URL}/alerts/trigger/", 
                               json={'lat': 15.0, 'lng': 75.0, 'threat_level': 'HIGH'}, 
                               headers=headers)
    alert_id = trigger_res.json()['alert_id']
    e_token = trigger_res.json()['emergency_token']
    print(f"Alert ID: {alert_id}, SOS Token: {e_token}")

    # Create a mock file
    mock_file = io.BytesIO(b"Fake Handshake Video")
    mock_file.name = 'handshake.mp4'

    print("--- 3. PHASE 1: Uploading to Supabase API ---")
    files_cloud = {'file': ('handshake.mp4', mock_file, 'video/mp4')}
    data_cloud = {'alert_id': alert_id}
    res_cloud = requests.post(f"{BASE_URL}/evidence/upload/", data=data_cloud, files=files_cloud, headers=headers)
    
    if res_cloud.status_code != 201:
        print(f"❌ Phase 1 Failed: {res_cloud.text}")
        return
        
    public_url = res_cloud.json().get('public_url')
    print(f"✅ Phase 1 Success! Supabase URL: {public_url}")

    print("--- 4. PHASE 2: Sending URL to Live Tracker ---")
    pulse_data = {
        'emergency_token': e_token,
        'sequence': '1',
        'lat': '15.1',
        'lng': '75.1',
        'remote_url': str(public_url)
    }
    res_pulse = requests.post(f"{BASE_URL}/alerts/upload-chunk/", data=pulse_data, headers=headers)
    print(f"📡 Pulse Status: {res_pulse.status_code}")
    try:
        print(f"📡 Pulse Response: {res_pulse.json()}")
    except:
        print(f"📡 Pulse Raw Output: {res_pulse.text}")

    if res_pulse.status_code == 200 and res_pulse.json().get('video_synced') is True:
        print("\n✅ SUCCESS: Handshake Architecture is Fully Operational!")
    else:
        print("\n❌ FAILURE: Live tracker did not sync the remote video URL.")

if __name__ == '__main__':
    verify_handshake()
