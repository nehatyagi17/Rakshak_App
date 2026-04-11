import os
import django
import json
from bson.objectid import ObjectId

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from core.db import users_col, alerts_col, contacts_col
from alerts.models import Incident
from alerts.views import send_emergency_email, get_nearby_users, send_expo_push

def run_diagnostic():
    print("🚦 RAKSHAK: Starting Deep SOS Diagnostic Tool...")
    
    # 1. Identification check
    test_email = "test2@test.com"
    print(f"\n1️⃣ Checking Identity: {test_email}")
    django_user = User.objects.filter(email=test_email).first()
    if not django_user:
        print("❌ FAIL: User not found in Django SQLite.")
        return
    print(f"✅ User found: {django_user.username} (ID: {django_user.id})")

    user_doc = users_col.find_one({"email": test_email})
    if not user_doc:
        print("❌ FAIL: User not found in MongoDB.")
        return
    print(f"✅ User document found in MongoDB (ID: {user_doc['_id']})")

    # 2. Mock Alert Record
    print("\n2️⃣ Creating Mock Alert...")
    mock_id = str(ObjectId())
    alert_doc = {
        "_id": ObjectId(mock_id),
        "user_id": django_user.id,
        "status": "created",
        "lat": 12.97,
        "lng": 77.59,
        "threat_level": "HIGH"
    }
    alerts_col.insert_one(alert_doc)
    print(f"✅ Mock Alert created with ID: {mock_id}")

    # 3. Simulate AlertVerify Logic (The Crash Point)
    print("\n3️⃣ Simulating 'AlertVerifyView' Logic...")
    try:
        # Step A: Update Status
        alerts_col.update_one({"_id": ObjectId(mock_id)}, {"$set": {"status": "active"}})
        print("   - Alert status set to 'active'")

        # Step B: Create Incident
        print("   - Attempting Incident.objects.create...")
        # CRITICAL CHECK: Does 'victim' require a User object or ID?
        incident = Incident.objects.create(victim=django_user, status='Active')
        print(f"   ✅ Incident Object Created: {incident.id}")
        print(f"   🎟️ Emergency Token: {incident.emergency_token}")

        # Step C: Proximity logic
        print("   - Attempting get_nearby_users...")
        nearby = get_nearby_users(12.97, 77.59, 2000)
        print(f"   ✅ Proximity Engine returned: {len(nearby)} users")

        # Step D: Notification simulation
        print("   - Attempting to send mock push (Try/Catch Guard)...")
        try:
           send_expo_push("SIMULATED_TOKEN", "Test", "Test Body")
           print("   ✅ Notification Logic functional.")
        except Exception as push_err:
           print(f"   ℹ️ INFO: Push skipped as expected (Fake token): {push_err}")

        print("\n✨ DIAGNOSTIC RESULT: SUCCESS.")
        print("The backend logic IS functional when running as a standalone script.")
        print("The 500 error on the server must be a Context/Middleware issue or a hidden NameError.")

    except Exception as e:
        print(f"\n💥 CRASH DETECTED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()
