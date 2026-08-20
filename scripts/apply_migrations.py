import os
import psycopg2

def run():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/songs_db")
    # If db_url has host 'db' and running outside docker, fallback to localhost
    print(f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    migrations = [
        "migrations/auth_phase1_migration.sql",
        "migrations/auth_phase3_migration.sql",
        "migrations/auth_phase4_migration.sql",
        "migrations/lyrics_columns_migration.sql"
    ]

    for m in migrations:
        try:
            with open(m, 'r') as f:
                sql = f.read()
            print(f"Running {m}...")
            cursor.execute(sql)
            print("Success.")
        except Exception as e:
            print(f"Failed or already applied {m}: {e}")

if __name__ == "__main__":
    run()
