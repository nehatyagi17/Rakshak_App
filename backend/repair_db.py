
import sqlite3
import os

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(users_rakshakprofile)")
    columns = [row[1] for row in cursor.fetchall()]
    
    modified = False
    if 'face_signature_url' not in columns:
        print("Adding face_signature_url...")
        cursor.execute("ALTER TABLE users_rakshakprofile ADD COLUMN face_signature_url TEXT")
        modified = True
    
    if 'biometric_active' not in columns:
        print("Adding biometric_active...")
        cursor.execute("ALTER TABLE users_rakshakprofile ADD COLUMN biometric_active BOOLEAN DEFAULT FALSE")
        modified = True
        
    if modified:
        conn.commit()
        print("✅ Database Repaired Successfully.")
    else:
        print("Database already has the required columns.")
    
    conn.close()
else:
    print("db.sqlite3 not found!")
