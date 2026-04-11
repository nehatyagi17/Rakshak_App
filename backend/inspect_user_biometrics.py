from pymongo import MongoClient
import os

# MongoDB Connection (Match core.db)
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client['rakshak_db']
users_col = db['users']

def inspect():
    print("--- RAKSHAK BIOMETRIC INSPECTION SYSTEM ---")
    users = users_col.find({})
    count = 0
    enrolled_count = 0
    
    for user in users:
        count += 1
        email = user.get('email', 'UNKNOWN')
        has_bio = 'biometric_vector' in user
        vector_len = len(user['biometric_vector']) if has_bio else 0
        
        status = f"ENROLLED ({vector_len}D)" if has_bio else "MISSING"
        if has_bio: enrolled_count += 1
        
        print(f"User: {email: <30} | Biometric: {status}")

    print("-" * 45)
    print(f"Total Users: {count} | Total Enrolled: {enrolled_count}")

if __name__ == "__main__":
    inspect()
