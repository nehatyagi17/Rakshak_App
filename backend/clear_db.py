import os
import django
from pymongo import MongoClient
from decouple import config

# 1. Setup Django environment for SQLite
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import call_command

def clear_all_data():
    print("🧨 RAKSHAK: Starting Full Database Purge...")
    
    # --- Part 1: Clear Django SQLite Data ---
    try:
        print("📁 Clearing SQLite (Django ORM)...")
        call_command('flush', '--no-input')
        print("✅ SQLite cleared.")
    except Exception as e:
        print(f"❌ SQLite clearing failed: {e}")

    # --- Part 2: Clear MongoDB Data ---
    try:
        print("🍃 Clearing MongoDB (PyMongo)...")
        MONGODB_URI = config('MONGODB_URI', default='mongodb://localhost:27017/rakshak')
        client = MongoClient(MONGODB_URI)
        db = client.get_database()
        
        collections = ['users', 'alerts', 'contacts', 'evidence', 'sessions', 'notifications']
        for col in collections:
            result = db[col].delete_many({})
            print(f"✅ Collection '{col}': {result.deleted_count} documents deleted.")
            
        print("✅ MongoDB cleared.")
    except Exception as e:
        print(f"❌ MongoDB clearing failed: {e}")

    print("\n✨ SYSTEM CLEAN: All development data has been purged.")

if __name__ == "__main__":
    clear_all_data()
