from app.core.database import engine
from app.models.history import ListeningHistory

def create_history_table():
    try:
        ListeningHistory.__table__.create(engine, checkfirst=True)
        print("Successfully created listening_history table!")
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    create_history_table()
