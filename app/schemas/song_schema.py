from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from app.services.url_signer import generate_signed_url

class SongBase(BaseModel):
    song_name: str
    artist_name: str
    original_music_link: Optional[str] = None
    instrumental_music_link: Optional[str] = None
    cover_url: Optional[str] = None
    has_lrc: bool = False
    has_full_lyrics: bool = False
    full_lyrics_format: Optional[str] = None
    r2_folder: Optional[str] = None
    lyrics_updated_at: Optional[datetime] = None
    lrc_url: Optional[str] = None
    full_lyrics_url: Optional[str] = None

class SongCreate(SongBase):
    pass

class SyncLyricsRequest(BaseModel):
    folder_name: Optional[str] = None
    song_id: Optional[UUID] = None
    song_name: Optional[str] = None
    has_lrc: Optional[bool] = None
    r2_lrc_link: Optional[str] = None
    has_full_lyrics: Optional[bool] = None
    full_lyrics_format: Optional[str] = None  # 'txt' | 'json'
    r2_full_lyrics_link: Optional[str] = None

class SongResponse(SongBase):
    id: UUID
    play_count: int
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def compute_lrc_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            has_lrc = data.get('has_lrc', False)
            has_full = data.get('has_full_lyrics', False)
            orig = data.get('original_music_link')
            r2_folder = data.get('r2_folder')
            fmt = data.get('full_lyrics_format') or 'txt'

            if has_lrc and not data.get('lrc_url'):
                if data.get('r2_lrc_link'):
                    data['lrc_url'] = data['r2_lrc_link']
                elif r2_folder:
                    data['lrc_url'] = f"https://music.ifreaky.us/{r2_folder}/lyrics.lrc"
                elif orig and 'original.mp3' in orig:
                    data['lrc_url'] = orig.replace('original.mp3', 'lyrics.lrc')

            if has_full and not data.get('full_lyrics_url'):
                if data.get('r2_full_lyrics_link'):
                    data['full_lyrics_url'] = data['r2_full_lyrics_link']
                elif r2_folder:
                    data['full_lyrics_url'] = f"https://music.ifreaky.us/{r2_folder}/full_lyrics.{fmt}"
                elif orig and 'original.mp3' in orig:
                    data['full_lyrics_url'] = orig.replace('original.mp3', f'full_lyrics.{fmt}')
        return data

    @field_validator('original_music_link', 'instrumental_music_link', 'cover_url', 'lrc_url', 'full_lyrics_url', mode='before')
    @classmethod
    def sign_url(cls, v: Optional[str]) -> Optional[str]:
        if v:
            custom_domain_url = v.replace("https://pub-e3eaa10382ee4950bafe2536fdfede82.r2.dev", "https://music.ifreaky.us")
            return generate_signed_url(custom_domain_url)
        return v

    model_config = ConfigDict(from_attributes=True)
