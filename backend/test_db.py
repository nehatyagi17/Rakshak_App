from pymongo import MongoClient
from decouple import config
import os
import sys

def test_db():
    try:
        uri = config("MONGODB_URI")
        print(f"Testing URI: {uri[:20]}...")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Force a connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful.")
        
        db = client["rakshak_db"]
        users_col = db["users"]
        count = users_col.count_documents({})
        print(f"✅ Found {count} users in the database.")
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_db()
