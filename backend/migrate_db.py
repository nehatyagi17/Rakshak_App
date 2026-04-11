import os
import django
import sys

# Setup django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.db import users_col
import pymongo

def migrate():
    print("Creating 2dsphere index...")
    try:
        users_col.create_index([("location", pymongo.GEOSPHERE)])
        print("✅ Index created successfully!")
    except Exception as e:
        print(f"❌ Error creating index: {e}")

    print("\nMigrating existing user coordinates to GeoJSON...")
    updated = 0
    # Search for anything that isn't a GeoJSON Point (type: object, and has lat or lng inside location)
    for user in users_col.find({"location": {"$exists": True}}):
        loc = user.get("location")
        # If it's a legacy flat dictionary {'lat': ..., 'lng': ...}
        if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
            try:
                lat = float(loc["lat"])
                lng = float(loc["lng"])
                users_col.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"location": {"type": "Point", "coordinates": [lng, lat]}}}
                )
                updated += 1
            except Exception as e:
                print(f"Skipping user {user.get('email')}: {e}")
        elif isinstance(loc, dict) and loc.get("type") == "Point":
             pass # Already BioJSON
    
    print(f"✅ Migrated {updated} users to GeoJSON Point format.")

if __name__ == '__main__':
    migrate()
