from pymongo import MongoClient
import os
from decouple import config

class MongoDBClient:
    _instance = None
    
    @classmethod
    def get_client(cls):
        if cls._instance is None:
            try:
                # When testing locally without .env, default to local if not set
                uri = config("MONGODB_URI", default="mongodb://localhost:27017")
                cls._instance = MongoClient(uri, serverSelectionTimeoutMS=5000)
                # Trigger a connection check
                cls._instance.admin.command('ping')
            except Exception as e:
                import logging
                logger = logging.getLogger('django')
                logger.error(f"❌ DATABASE CONNECTION FAILURE: {e}")
                # We still return the client object, but operations will fail gracefully later
                # or we could return None, but many parts of the app expect a client.
        return cls._instance

client = MongoDBClient.get_client()
db = client["rakshak_db"]

users_col = db["users"]
contacts_col = db["trusted_contacts"]
keywords_col = db["distress_keywords"]
alerts_col = db["alerts"]
evidence_col = db["evidence"]
logs_col = db["alert_logs"]
