import sys
import os
import re
import uuid
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from pathlib import Path

# Add the parent directory to sys.path to allow importing from app
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal, Base, engine
from app.models.song import Song

# Same logic used in your orchestrator
def check_if_exists_in_r2(filename: str) -> bool:
    r2_url = f"https://pub-e3eaa10382ee4950bafe2536fdfede82.r2.dev/originals/{filename}"
    try:
        resp = requests.head(r2_url, timeout=5)
        return resp.status_code == 200
    except:
        return False

def get_r2_urls(filename: str):
    """Generate both original and instrumental R2 URLs based on the filename"""
    orig_url = f"https://pub-e3eaa10382ee4950bafe2536fdfede82.r2.dev/originals/{filename}"
    
    # In orchestrator, instrumental files usually have '_instrumental' added to the base name
    base_name = os.path.splitext(filename)[0]
    inst_url = f"https://pub-e3eaa10382ee4950bafe2536fdfede82.r2.dev/instrumentals/{base_name}_instrumental.mp3"
    
    return orig_url, inst_url

def fetch_sitemap_urls():
    sitemap_url = "https://sarigama.lk/sitemap.xml"
    print(f"[+] Fetching sitemap from {sitemap_url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(sitemap_url, headers=headers)
    if response.status_code != 200:
        print("[-] Failed to fetch sitemap.")
        return []

    root = ET.fromstring(response.text)
    namespace = ""
    if "}" in root.tag:
        namespace = root.tag.split("}")[0] + "}"

    song_urls = []
    for url in root.findall(f"{namespace}url"):
        loc = url.find(f"{namespace}loc")
        if loc is not None and loc.text and "/sinhala-song/" in loc.text:
            song_urls.append(loc.text)

    print(f"[+] Found {len(song_urls)} Sinhala song URLs in sitemap.")
    return song_urls

def extract_song_metadata(url: str):
    """Scrapes the song page to get the title and artist"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract Song Name
        title_div = soup.find('div', class_='page-title')
        song_name = "Unknown Song"
        if title_div:
            h1_tag = title_div.find('h1', itemprop='name', class_='inline')
            if h1_tag:
                song_name = h1_tag.text.strip()
                
        # 2. Extract Artist Name
        artist_span = soup.find('span', itemprop='byArtist')
        artist_name = artist_span.text.strip() if artist_span else "Unknown Artist"
        
        return song_name, artist_name
    except Exception as e:
        print(f"[-] Error extracting metadata from {url}: {e}")
        return None, None

def run_sync():
    # Initialize Database
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # NEW OPTIMIZATION: Fetch all R2 files first to save thousands of HTTP requests!
    print("\n[+] Fetching existing files from R2...")
    try:
        from app.services.r2_storage import list_files
        r2_files_data = list_files(prefix="originals/", max_files=15000)
        # Create a fast lookup set of just the file names
        r2_filenames = set([f['file_name'].replace("originals/", "") for f in r2_files_data])
        print(f"[+] Found {len(r2_filenames)} original songs in R2.")
    except Exception as e:
        print(f"[-] Could not load R2 files: {e}")
        r2_filenames = set()

    song_urls = fetch_sitemap_urls()
    
    added_count = 0
    skipped_count = 0
    
    print("\n[+] Starting Database Sync...\n")
    
    for i, url in enumerate(song_urls):
        # Predict the filename base from the URL slug
        slug = urlparse(url).path.split("/")[-2].lower()
        
        # The URL slug uses hyphens, but the downloaded files use underscores. 
        # Example: 'a-ra-sulande' -> 'a_ra_sulande'
        slug_underscores = slug.replace("-", "_")
        slug_underscores = re.sub(r'(?i)[_\-\.]?sarigama[_\-\.]?(lk)?', '', slug_underscores)
        
        # Find if this slug exists inside ANY of the actual R2 filenames (which also contain artist names)
        # E.g. Does "a_ra_sulande" exist in "a_ra_sulande_nirosha_virajini.mp3"?
        matched_r2_filename = None
        for r2_name in r2_filenames:
            if slug_underscores in r2_name.lower():
                matched_r2_filename = r2_name
                break
                
        # Check if we found a match
        if matched_r2_filename:
            print(f"\n[{i+1}/{len(song_urls)}] [✓] Match found! URL slug '{slug}' -> R2 File: '{matched_r2_filename}'")
            
            # Since it exists, fetch the HTML page for metadata
            song_name, artist_name = extract_song_metadata(url)
            
            if song_name and artist_name:
                print(f"    -> Extracted HTML Data: '{song_name}' by '{artist_name}'")
                
                # Check if we already have it in the DB to avoid duplicates
                existing_song = db.query(Song).filter(Song.song_name == song_name, Song.artist_name == artist_name).first()
                
                if not existing_song:
                    orig_url, inst_url = get_r2_urls(matched_r2_filename)
                    
                    new_song = Song(
                        id=uuid.uuid4(),
                        song_name=song_name,
                        artist_name=artist_name,
                        original_music_link=orig_url,
                        instrumental_music_link=inst_url
                    )
                    db.add(new_song)
                    db.commit()
                    print("    -> Added to Database!")
                    added_count += 1
                else:
                    print("    -> Already exists in Database, skipping.")
                    
        else:
            # If not in R2, we just pass
            skipped_count += 1
            # Print a status every 1000 skipped songs so you know it's working
            if skipped_count % 1000 == 0:
                print(f"[{i+1}/{len(song_urls)}] ... still scanning (skipped {skipped_count} missing files) ...")
            
    print(f"\n[+] Sync Complete! Added {added_count} new songs to the database. (Skipped {skipped_count} missing from R2)")
    db.close()

if __name__ == "__main__":
    run_sync()
