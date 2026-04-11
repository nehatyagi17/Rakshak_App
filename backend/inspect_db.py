from pymongo import MongoClient
from decouple import config
import os
import sys

def inspect_user():
    try:
        uri = config("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client["rakshak_db"]
        users_col = db["users"]
        
        email = "test001@example.com"
        user = users_col.find_one({"email": email})
        if user:
            print(f"✅ User found: {user['email']}")
            print(f"Password Hash (first 5 chars): {user['password'][:5]}...")
            print(f"Stored Name: {user.get('name')}")
            print(f"Stored Phone: {user.get('phone')}")
        else:
            print(f"❌ User '{email}' NOT FOUND in 'rakshak_db.users'")
            # List some users to see what's there
            print("Listing last 5 users:")
            for u in users_col.find().sort("_id", -1).limit(5):
                print(f"- {u.get('email')} (ID: {u['_id']})")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    inspect_user()
