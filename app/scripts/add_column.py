from app.core.database import engine
from sqlalchemy import text

def add_play_count_column():
    with engine.connect() as conn:
        # Check if the column exists first
        try:
            conn.execute(text("ALTER TABLE songs ADD COLUMN play_count INTEGER DEFAULT 0;"))
            conn.execute(text("CREATE INDEX ix_songs_play_count ON songs (play_count);"))
            conn.commit()
            print("Successfully added play_count column to songs table!")
        except Exception as e:
            print("Column might already exist or an error occurred:", e)

if __name__ == "__main__":
    add_play_count_column()
