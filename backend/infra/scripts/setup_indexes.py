import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from decouple import config

def setup_indexes():
    print("Connecting to MongoDB Database...")
    mongo_uri = config("MONGODB_URI", default=None)
    if not mongo_uri:
        print("Error: MONGODB_URI not set in .env")
        return

    client = MongoClient(mongo_uri)
    db = client["rakshak_db"]
    
    print("Setting up indexes for users collection...")
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("phone", ASCENDING)], unique=True)
    db.users.create_index([("location", "2dsphere")])
    db.users.create_index([("expo_push_token", ASCENDING)])
    
    print("Setting up indexes for alerts collection...")
    db.alerts.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    db.alerts.create_index([("location", "2dsphere")])
    db.alerts.create_index([("user_id", ASCENDING)])
    
    print("Setting up indexes for trusted_contacts...")
    db.trusted_contacts.create_index([("user_id", ASCENDING)])
    
    print("Setting up indexes for evidence...")
    db.evidence.create_index([("alert_id", ASCENDING)])
    db.evidence.create_index([("user_id", ASCENDING)])
    
    print("Setting up indexes for alert_logs...")
    db.alert_logs.create_index([("alert_id", ASCENDING), ("timestamp", DESCENDING)])
    
    print("All indexes have been successfully created.")

if __name__ == "__main__":
    setup_indexes()
