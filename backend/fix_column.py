import sqlite3

db_path = 'c:/Users/rawat/OneDrive/Desktop/Rakshak/backend/db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE users_rakshakprofile ADD COLUMN safety_keyword varchar(50) DEFAULT 'emergency';")
    conn.commit()
    print("Column safety_keyword added successfully.")
except sqlite3.OperationalError as e:
    print(f"Error: {e}")
conn.close()
