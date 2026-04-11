import requests
import json
import io

BASE_URL = 'http://127.0.0.1:8000/api'
creds = {'email': 'admin@rakshak.system', 'password': 'admin123'}

def verify_dual_upload():
    print("--- 1. Logging In ---")
    login_res = requests.post(f"{BASE_URL}/auth/login/", json=creds)
    token = login_res.json()['access']
    headers = {'Authorization': f'Bearer {token}'}

    print("--- 2. Triggering SOS ---")
    trigger_res = requests.post(f"{BASE_URL}/alerts/trigger/", 
                               json={'lat': 20.0, 'lng': 80.0, 'threat_level': 'CRITICAL'}, 
                               headers=headers)
    alert_id = trigger_res.json()['alert_id']
    e_token = trigger_res.json()['emergency_token']
    print(f"Alert ID: {alert_id}, SOS Token: {e_token}")

    # Create a mock file
    mock_file = io.BytesIO(b"Fake Video Data Chunk")
    mock_file.name = 'test_chunk.mp4'

    print("--- 3. Simulating Upload to Local Tracker ---")
    files = {'file': ('test_chunk.mp4', mock_file, 'video/mp4')}
    data = {
        'emergency_token': e_token,
        'sequence': '1',
        'lat': '20.1',
        'lng': '80.1'
    }
    res_local = requests.post(f"{BASE_URL}/alerts/upload-chunk/", data=data, files=files, headers=headers)
    print(f"Local Tracker Status: {res_local.status_code}")

    # Re-seek mock file for second upload
    mock_file.seek(0)

    print("--- 4. Simulating Upload to Supabase Cloud ---")
    files_cloud = {'file': ('test_chunk.mp4', mock_file, 'video/mp4')}
    data_cloud = {'alert_id': alert_id}
    res_cloud = requests.post(f"{BASE_URL}/evidence/upload/", data=data_cloud, files=files_cloud, headers=headers)
    print(f"Cloud Store Status: {res_cloud.status_code} | {res_cloud.text[:100]}")

    print("--- 5. Verifying DB Records ---")
    
    # Check if tracking updated
    list_res = requests.get(f"{BASE_URL}/alerts/admin/list/", headers=headers).json()
    alert = next((a for a in list_res if a['_id'] == alert_id), None)
    if alert and alert['lat'] == 20.1:
        print("✅ Local Tracking: OK")
    else:
        print("❌ Local Tracking: FAILED")

    # Check if evidence record created
    evidence_res = requests.get(f"{BASE_URL}/evidence/{alert_id}/", headers=headers).json()
    if len(evidence_res) > 0:
        print(f"✅ Cloud Evidence Record: OK (Found {len(evidence_res)} items)")
        print(f"   Stored URL: {evidence_res[0].get('public_url')}")
    else:
        print("❌ Cloud Evidence Record: FAILED")

if __name__ == '__main__':
    verify_dual_upload()
