import os
import sys
import bcrypt
from pymongo import MongoClient
from decouple import config

# Ensure we're in the backend dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def sync_accounts():
    try:
        uri = config("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client["rakshak_db"]
        users_col = db["users"]
        
        accounts = [
            {
                "email": "admin@rakshak.system",
                "password": "admin123",
                "name": "System Admin",
                "phone": "0000000000",
                "is_admin": True
            },
            {
                "email": "user@rakshak.ai",
                "password": "password123",
                "name": "Test User",
                "phone": "9876543210",
                "is_admin": False
            }
        ]
        
        for acc in accounts:
            existing = users_col.find_one({"email": acc["email"]})
            hashed = bcrypt.hashpw(acc["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            doc = {
                "email": acc["email"],
                "password": hashed,
                "name": acc["name"],
                "phone": acc["phone"],
                "is_admin": acc["is_admin"],
                "expo_push_token": None,
                "location": {"lat": 28.6139, "lng": 77.2090}
            }
            
            if existing:
                users_col.update_one({"email": acc["email"]}, {"$set": doc})
                print(f"🔄 Updated: {acc['email']}")
            else:
                users_col.insert_one(doc)
                print(f"✨ Created: {acc['email']}")
                
        print("\n✅ Database Sync Complete!")
        
    except Exception as e:
        print(f"❌ Sync Error: {str(e)}")

if __name__ == "__main__":
    sync_accounts()
