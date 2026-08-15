from app.core.database import engine
from app.models.user import user_favorite_songs

def create_favorites_table():
    try:
        # Create just the user_favorite_songs table
        user_favorite_songs.create(engine, checkfirst=True)
        print("Successfully created user_favorite_songs table!")
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    create_favorites_table()
