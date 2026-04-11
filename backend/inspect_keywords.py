import sqlite3
import pymongo
import os
from pprint import pprint
from bson.objectid import ObjectId

# SQLite
db_path = 'c:/Users/rawat/OneDrive/Desktop/Rakshak/backend/db.sqlite3'
if os.path.exists(db_path):
    print("--- SQLite 'users_rakshakprofile' ---")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, rakshak_id, safety_keyword FROM users_rakshakprofile")
    for row in cursor.fetchall():
        print(row)
    conn.close()

# MongoDB
print("\n--- MongoDB 'users' ---")
try:
    from decouple import config
    MONGO_URI = config("MONGO_URI", default="mongodb://localhost:27017")
    client = pymongo.MongoClient(MONGO_URI)
    db = client["rakshak_db"]
    users_col = db["users"]
    
    for user in users_col.find():
        print({
            "_id": str(user.get("_id")),
            "email": user.get("email"),
            "rakshak_id": user.get("rakshak_id"),
            "safety_keyword": user.get("safety_keyword")
        })
except Exception as e:
    print("MongoDB Error:", e)
