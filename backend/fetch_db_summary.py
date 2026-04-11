from pymongo import MongoClient
from decouple import config
import json
from bson import ObjectId
import sys

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, bytes):
            return o.decode('utf-8', errors='ignore')
        return str(o)

def fetch_summary():
    try:
        uri = config("MONGODB_URI")
        print(f"Connecting to: {uri.split('@')[-1]}") # Hide credentials
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB Connection Successful!")
        
        dbs = client.list_database_names()
        print(f"Databases found: {dbs}")
        
        target_db = "rakshak_db"
        if target_db not in dbs:
            print(f"⚠️  Database '{target_db}' not found. Using the first non-system database if available.")
            # Skip system dbs
            available_dbs = [d for d in dbs if d not in ['admin', 'local', 'config']]
            if available_dbs:
                target_db = available_dbs[0]
                print(f"Switching to database: {target_db}")
            else:
                print("No user databases found.")
                return

        db = client[target_db]
        print(f"\n--- Database: {target_db} ---")
        
        collections = db.list_collection_names()
        print(f"Collections found: {collections}")
        
        for coll_name in collections:
            print(f"\n[Collection: {coll_name}]")
            col = db[coll_name]
            count = col.count_documents({})
            print(f"Total Documents: {count}")
            
            # Fetch last 5 documents
            docs = list(col.find().sort("_id", -1).limit(5))
            if docs:
                print(f"Latest {len(docs)} documents:")
                for d in docs:
                    # Clean up long fields like passwords for display
                    if 'password' in d:
                        d['password'] = d['password'][:10] + "..."
                    print(json.dumps(d, indent=2, cls=JSONEncoder))
            else:
                print("No documents found.")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fetch_summary()
