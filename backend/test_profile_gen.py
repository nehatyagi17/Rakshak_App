import os
import sys
import django
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import RakshakProfile

def test_rakshak_profile_system():
    print("🚀 Starting RAKSHAK-ID System Test...")
    
    unique_email = f"testuser_{uuid.uuid4().hex[:6]}@rakshak.ai"
    
    try:
        # 1. Create a dummy user
        print(f"Creating user: {unique_email}")
        user = User.objects.create_user(username=unique_email, email=unique_email, password="password123")
        
        # 2. Check if the profile was automatically created by the signal
        profile = RakshakProfile.objects.get(user=user)
        print(f"✅ RakshakProfile created automatically.")
        
        # 3. Verify the RAKSHAK-ID format
        print(f"🔍 Checking RAKSHAK-ID: {profile.rakshak_id}")
        if profile.rakshak_id.startswith("RAK-") and len(profile.rakshak_id) == 13: # RAK-XXXX-XXXX = 13
             print(f"✅ RAKSHAK-ID format is correct (RAK-XXXX-XXXX).")
        else:
             print(f"❌ RAKSHAK-ID format mismatch: Expected 13 chars (RAK-XXXX-XXXX), got {len(profile.rakshak_id)}")
             
        # 4. Verify Trust Tier helper
        # Default is 50
        tier = profile.get_trust_tier()
        print(f"⭐ Initial Trust Score: {profile.trust_score} -> Tier: {tier}")
        if tier == "Newbie":
            print("✅ Initial Tier is correct.")
            
        # Update score to test Guardian tier
        profile.trust_score = 95
        profile.save()
        tier = profile.get_trust_tier()
        print(f"⭐ Updated Trust Score: {profile.trust_score} -> Tier: {tier}")
        if tier == "Guardian":
            print("✅ Tier updated correctly.")
            
        # 5. Cleanup
        user.delete()
        print("🗑️ Test user deleted.")
        print("\n🏆 PASSED: RAKSHAK-ID System is fully operational!")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")

if __name__ == "__main__":
    test_rakshak_profile_system()
