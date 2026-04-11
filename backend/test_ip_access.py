import requests
import json

# Testing with the Local IP that the phone uses
url = "http://192.168.48.21:8000/api/auth/login/"
payload = {
    "email": "test2@test.com",
    "password": "123456"
}
headers = {"Content-Type": "application/json"}

print(f"Checking access via Local IP: {url}")
try:
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"ERROR: Could not connect to local IP. This usually means a Firewall is blocking port 8000 or the server isn't listening on the external interface.")
    print(f"Detail: {e}")
