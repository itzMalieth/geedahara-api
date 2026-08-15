from app.core.database import engine
from sqlalchemy import text

def update_users_table():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ALTER COLUMN google_id DROP NOT NULL;"))
            print("Successfully made google_id optional.")
        except Exception as e:
            print("Error altering google_id:", e)
            
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR;"))
            print("Successfully added hashed_password column.")
        except Exception as e:
            print("Error adding hashed_password (might already exist):", e)
            
        conn.commit()

if __name__ == "__main__":
    update_users_table()
