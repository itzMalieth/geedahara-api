import uuid
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.database import Base

class Song(Base):
    __tablename__ = "songs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    song_name = Column(String, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    instrumental_music_link = Column(String, nullable=True)
    original_music_link = Column(String, nullable=True)
    cover_url = Column(String, nullable=True)
    play_count = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    r2_lrc_link = Column(String, nullable=True)
    r2_full_lyrics_link = Column(String, nullable=True)
    
    # Verified lyrics tracking
    has_lrc = Column(Boolean, default=False, index=True, nullable=False)
    has_full_lyrics = Column(Boolean, default=False, index=True, nullable=False)
    full_lyrics_format = Column(String, nullable=True) # 'txt' | 'json'
    r2_folder = Column(String, index=True, nullable=True) # folder slug in R2
    lyrics_updated_at = Column(DateTime(timezone=True), index=True, nullable=True)

    @property
    def lrc_url(self):
        if self.has_lrc:
            if self.r2_lrc_link:
                return self.r2_lrc_link
            if self.r2_folder:
                return f"https://music.ifreaky.us/{self.r2_folder}/lyrics.lrc"
            if self.original_music_link and 'original.mp3' in self.original_music_link:
                return self.original_music_link.replace('original.mp3', 'lyrics.lrc')
        return None

    @property
    def full_lyrics_url(self):
        if self.has_full_lyrics:
            if self.r2_full_lyrics_link:
                return self.r2_full_lyrics_link
            ext = 'json' if self.full_lyrics_format == 'json' else 'txt'
            if self.r2_folder:
                return f"https://music.ifreaky.us/{self.r2_folder}/full_lyrics.{ext}"
            if self.original_music_link and 'original.mp3' in self.original_music_link:
                return self.original_music_link.replace('original.mp3', f'full_lyrics.{ext}')
        return None

# ==========================================
# Automated Meilisearch Sync (Event Listeners)
# ==========================================
from sqlalchemy import event
from sqlalchemy.orm import Session

def format_for_meili(song):
    return {
        "id": str(song.id),
        "song_name": song.song_name,
        "artist_name": song.artist_name,
        "original_music_link": song.original_music_link,
        "instrumental_music_link": song.instrumental_music_link,
        "cover_url": song.cover_url,
        "has_lrc": song.has_lrc,
        "has_full_lyrics": song.has_full_lyrics,
    }

# ------------------------------------------
# Songs index sync
# ------------------------------------------

@event.listens_for(Song, 'after_insert')
def sync_meili_insert(mapper, connection, target):
    try:
        from app.services.search import get_songs_index
        get_songs_index().add_documents([format_for_meili(target)])
    except Exception as e:
        print(f"[Meilisearch] Failed to sync song insert: {e}")

@event.listens_for(Song, 'after_update')
def sync_meili_update(mapper, connection, target):
    try:
        from app.services.search import get_songs_index
        get_songs_index().update_documents([format_for_meili(target)])
    except Exception as e:
        print(f"[Meilisearch] Failed to sync song update: {e}")

@event.listens_for(Song, 'after_delete')
def sync_meili_delete(mapper, connection, target):
    try:
        from app.services.search import get_songs_index
        get_songs_index().delete_document(str(target.id))
    except Exception as e:
        print(f"[Meilisearch] Failed to sync song delete: {e}")

# ------------------------------------------
# Artists index sync — fires after commit so
# the DB reflects the latest song count.
# ------------------------------------------

def _do_sync_artist(db_session, artist_name: str):
    """Sync a single artist to Meilisearch using a live DB session."""
    try:
        from app.services.search import sync_artist_to_meili
        sync_artist_to_meili(db_session, artist_name)
    except Exception as e:
        print(f"[Meilisearch] Artist sync error for '{artist_name}': {e}")


@event.listens_for(Song, 'after_insert')
def sync_artist_insert(mapper, connection, target):
    """After a new song is committed, upsert the artist in Meilisearch."""
    artist_name = target.artist_name
    if not artist_name:
        return
    # Attach a post-commit hook so the song_count query sees the committed row
    session = Session.object_session(target)
    if session is None:
        return

    @event.listens_for(session, 'after_commit', once=True)
    def after_commit(sess):
        # Re-open a quick session to query the committed count
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            _do_sync_artist(db, artist_name)
        finally:
            db.close()


@event.listens_for(Song, 'after_update')
def sync_artist_update(mapper, connection, target):
    """After a song is updated, re-sync the artist (handles artist_name changes)."""
    artist_name = target.artist_name
    if not artist_name:
        return
    session = Session.object_session(target)
    if session is None:
        return

    # Capture the old artist name if it was changed
    history = target.__dict__.get('_sa_instance_state')
    old_artist = None
    try:
        from sqlalchemy import inspect as sa_inspect
        state = sa_inspect(target)
        attr = state.attrs.artist_name
        old_artist = attr.history.deleted[0] if attr.history.deleted else None
    except Exception:
        pass

    @event.listens_for(session, 'after_commit', once=True)
    def after_commit(sess):
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            _do_sync_artist(db, artist_name)
            if old_artist and old_artist != artist_name:
                # Old artist may have lost a song — re-sync their count too
                _do_sync_artist(db, old_artist)
        finally:
            db.close()


@event.listens_for(Song, 'after_delete')
def sync_artist_delete(mapper, connection, target):
    """After a song is deleted, decrement (or remove) the artist in Meilisearch."""
    artist_name = target.artist_name
    if not artist_name:
        return
    session = Session.object_session(target)
    if session is None:
        return

    @event.listens_for(session, 'after_commit', once=True)
    def after_commit(sess):
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            _do_sync_artist(db, artist_name)
        finally:
            db.close()
