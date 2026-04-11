from pymongo import MongoClient
from decouple import config

def list_users():
    try:
        uri = config("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        db = client["rakshak_db"]
        users = db["users"].find({}, {"email": 1, "name": 1, "phone": 1})
        print("DATABASE USERS:")
        for u in users:
            print(f"- {u['email']} | Name: {u.get('name')} | Phone: {u.get('phone')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_users()
