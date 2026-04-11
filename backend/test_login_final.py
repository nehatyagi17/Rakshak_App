import requests
import json

url = "http://127.0.0.1:8000/api/auth/login/"
payload = {
    "email": "test2@test.com",
    "password": "123456"
}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response (First 1000 chars):")
    print(response.text[:1000])
except Exception as e:
    print(f"Error: {e}")
