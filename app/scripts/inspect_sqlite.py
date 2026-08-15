import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sarigama_uploads.db"))
print(f"Database path: {db_path}")

if not os.path.exists(db_path):
    print("Database file not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print(f"Tables found: {[t[0] for t in tables]}\n")

for (table_name,) in tables:
    print(f"=== Table: {table_name} ===")
    columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    for col in columns:
        print(f"  Column: {col[1]} ({col[2]})")
    
    count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"  Total records: {count}")
    
    sample = cursor.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
    print("  Sample records:")
    for row in sample:
        print(f"    {row}")
    print()

conn.close()
