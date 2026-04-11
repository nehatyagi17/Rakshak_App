import os
import django
import sys
from bson.objectid import ObjectId

# Setup django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.db import users_col

def check_users():
    users = list(users_col.find())
    print(f"Checking {len(users)} users...")
    for user in users:
        print(f"User: {user.get('email')}")
        print(f"  ID: {user.get('_id')}")
        print(f"  Rakshak ID: {user.get('rakshak_id')}")
        print(f"  Last Seen via WS: {user.get('last_seen_ws')}")
        print(f"  Location: {user.get('location')}")
        print("-" * 20)

if __name__ == '__main__':
    check_users()
