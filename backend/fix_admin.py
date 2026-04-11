import os
import django
import bcrypt
import sys
from bson.objectid import ObjectId

# Setup django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import RakshakProfile
from core.db import users_col

def fix_admin():
    email = "admin@rakshak.system".strip().lower()
    password = "admin123"
    name = "System Admin"

    print(f"--- Synchronizing Admin: {email} ---")

    # 1. MongoDB Sync
    user_doc = users_col.find_one({"email": email})
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    if user_doc:
        print(f"✅ Found in MongoDB. Updating is_admin flag and password...")
        users_col.update_one(
            {"email": email}, 
            {"$set": {"is_admin": True, "password": hashed, "name": name}}
        )
    else:
        print(f"➕ Not found in MongoDB. Creating new record...")
        user_doc_new = {
            "email": email,
            "password": hashed,
            "name": name,
            "phone": "0000000000",
            "is_admin": True,
            "expo_push_token": None,
            "location": None
        }
        users_col.insert_one(user_doc_new)
        user_doc = users_col.find_one({"email": email})

    # 2. Django User Sync
    django_user, created = User.objects.get_or_create(email=email, defaults={'username': email})
    django_user.set_password(password)
    django_user.is_superuser = True
    django_user.is_staff = True
    django_user.save()
    
    if created:
        print(f"✅ Django Superuser created.")
    else:
        print(f"✅ Django Superuser updated.")

    # 3. RakshakProfile Sync
    from users.signals import generate_rakshak_id
    profile, p_created = RakshakProfile.objects.get_or_create(user=django_user)
    if not profile.rakshak_id:
        profile.rakshak_id = generate_rakshak_id()
        profile.save()
    
    # Update MongoDB with Rakshak ID
    users_col.update_one({"email": email}, {"$set": {"rakshak_id": profile.rakshak_id}})
    
    print(f"🚀 Admin Sync Complete! Rakshak ID: {profile.rakshak_id}")
    print(f"👉 Login with: {email} / {password}")

if __name__ == '__main__':
    fix_admin()
