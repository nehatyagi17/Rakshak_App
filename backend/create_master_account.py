from pymongo import MongoClient
import bcrypt
from decouple import config
import os
import sys

def create_master_account():
    try:
        uri = config("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client["rakshak_db"]
        users_col = db["users"]
        
        email = "admin@rakshak.system"
        password = "admin123"
        
        # Check if already exists
        if users_col.find_one({"email": email}):
            print(f"✅ Master account '{email}' already exists.")
            return

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user_doc = {
            "email": email,
            "password": hashed,
            "name": "System Admin",
            "phone": "0000000000",
            "expo_push_token": None,
            "location": None
        }
        
        result = users_col.insert_one(user_doc)
        print(f"✅ Master account '{email}' created successfully (ID: {result.inserted_id}).")
        
    except Exception as e:
        print(f"❌ Error creating master account: {str(e)}")

if __name__ == "__main__":
    create_master_account()
