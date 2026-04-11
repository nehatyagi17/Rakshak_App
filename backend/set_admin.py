import os
import sys
from bson.objectid import ObjectId

# Add the backend directory to path to import core
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.db import users_col

def set_admin_by_phone(phone, status=True):
    user = users_col.find_one({"phone": phone})
    if not user:
        print(f"❌ User with phone {phone} not found.")
        return
    
    users_col.update_one({"phone": phone}, {"$set": {"is_admin": status}})
    print(f"✅ User {user.get('name')} (phone: {phone}) is now {'an ADMIN' if status else 'NO LONGER an admin'}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_admin.py <phone_number> [true/false]")
        # List some users for convenience
        print("\nCurrent Users:")
        for u in users_col.find({}, {"name": 1, "phone": 1, "is_admin": 1}):
            print(f"- {u.get('name')} | {u.get('phone')} | Admin: {u.get('is_admin', False)}")
        sys.exit(1)
    
    phone_num = sys.argv[1]
    is_admin = True
    if len(sys.argv) > 2:
        is_admin = sys.argv[2].lower() == 'true'
    
    set_admin_by_phone(phone_num, is_admin)
