import sqlite3
import os

db_path = 'c:/Users/rawat/OneDrive/Desktop/Rakshak/backend/db.sqlite3'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users_rakshakprofile);")
    columns = cursor.fetchall()
    for col in columns:
        print(f"Column: {col[1]}")
    conn.close()
