import sys
import os
import uuid
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from pathlib import Path

# Add the parent directory to sys.path to allow importing from app
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal, Base, engine
from app.models.song import Song

# If they have r2_upload.py, we might want to copy it to lyrics-api/app/services later.
# For now, we mock the list_files or use a placeholder assuming r2_upload will be in services.
try:
    from app.services.r2_storage import list_files
except ImportError:
    print("Warning: R2 storage module not found in app.services, using dummy data for list_files if needed.")
    def list_files(prefix=""):
        return []

def init_db():
    Base.metadata.create_all(bind=engine)

def extract_metadata_from_html(html_content: str):
    """
    Extract song and artist name from the provided HTML content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract Song Name
    title_div = soup.find('div', class_='page-title')
    song_name = title_div.find('h1', itemprop='name').text.strip() if title_div and title_div.find('h1', itemprop='name') else "Unknown Song"
    
    # Extract Artist Name
    artist_span = soup.find('span', itemprop='byArtist')
    artist_name = artist_span.text.strip() if artist_span else "Unknown Artist"
    
    return song_name, artist_name

def extract_metadata_from_url(url: str):
    """
    Fetch HTML from URL and extract metadata.
    """
    response = requests.get(url)
    if response.status_code == 200:
        return extract_metadata_from_html(response.text)
    return "Unknown Song", "Unknown Artist"

def migrate_r2_data(html_directory_or_url: str = None):
    db: Session = SessionLocal()
    init_db()
    
    print("Fetching files from R2...")
    # Increase max_files to fetch all 1.2k+ songs
    r2_files = list_files(prefix="", max_files=2000)
    
    print(f"Found {len(r2_files)} files in R2.")
    
    for file_info in r2_files:
        url = file_info.get('url', '')
        file_name = file_info.get('file_name', '')
        
        # Example logic: determine if instrumental based on filename
        is_instrumental = "inst" in file_name.lower() or "karaoke" in file_name.lower()
        
        # NOTE: You'll need to define how to match the R2 file to its specific HTML page.
        # This is a placeholder for fetching that metadata.
        # song_name, artist_name = extract_metadata_from_url("YOUR_SONG_PAGE_URL")
        
        # Dummy extraction for demonstration:
        song_name, artist_name = "Sample Song", "Sample Artist" 
        
        # Create DB Record
        new_song = Song(
            id=uuid.uuid4(),
            song_name=song_name,
            artist_name=artist_name,
            instrumental_music_link=url if is_instrumental else None,
            original_music_link=url if not is_instrumental else None,
        )
        
        db.add(new_song)
        print(f"Added: {song_name} by {artist_name}")
    
    db.commit()
    print("Migration finished!")

if __name__ == "__main__":
    print("Starting migration process...")
    migrate_r2_data()
