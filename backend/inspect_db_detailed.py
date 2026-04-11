from pymongo import MongoClient
from decouple import config
import json
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

def show_users():
    try:
        uri = config("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client["rakshak_db"]
        
        print("\n=== [Collection: users] ===")
        users_col = db["users"]
        users = list(users_col.find())
        print(f"Total Users: {len(users)}")
        for u in users:
            # Mask sensitive data
            u['password'] = u['password'][:10] + "..." if 'password' in u else "N/A"
            print(json.dumps(u, indent=2, cls=JSONEncoder))

        print("\n=== [Collection: contacts] ===")
        contacts_col = db["contacts"]
        contacts = list(contacts_col.find())
        print(f"Total Contacts: {len(contacts)}")
        for c in contacts:
            print(json.dumps(c, indent=2, cls=JSONEncoder))

        print("\n=== [Collection: alerts] ===")
        alerts_col = db["alerts"]
        alerts = list(alerts_col.find().sort("_id", -1).limit(5))
        print(f"Total Alerts: {alerts_col.count_documents({})}")
        print("Last 5 Alerts:")
        for a in alerts:
            print(json.dumps(a, indent=2, cls=JSONEncoder))
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    show_users()
