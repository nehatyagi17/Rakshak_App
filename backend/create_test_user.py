import os
import sys
import bcrypt
from bson.objectid import ObjectId

# Add the backend directory to path to import core
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.db import users_col

def create_test_user():
    email = "user@rakshak.ai"
    password = "password123"
    
    # Check if already exists
    if users_col.find_one({"email": email}):
        print(f"✅ Test user '{email}' already exists.")
        return

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password": hashed,
        "name": "Test User",
        "phone": "9876543210",
        "is_admin": False,
        "expo_push_token": None,
        "location": {"lat": 28.6139, "lng": 77.2090} # New Delhi
    }
    
    result = users_col.insert_one(user_doc)
    print(f"✅ Test user '{email}' created successfully with password 'password123'.")

if __name__ == "__main__":
    create_test_user()
