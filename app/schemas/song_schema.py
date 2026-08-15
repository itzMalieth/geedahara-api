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
    lrc_url: Optional[str] = None

class SongCreate(SongBase):
    pass

class SongResponse(SongBase):
    id: UUID
    play_count: int
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def compute_lrc_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            orig = data.get('original_music_link')
            if orig and 'original.mp3' in orig and not data.get('lrc_url'):
                data['lrc_url'] = orig.replace('original.mp3', 'lyrics.lrc')
        elif hasattr(data, 'original_music_link'):
            orig = getattr(data, 'original_music_link', None)
            if orig and 'original.mp3' in orig and not getattr(data, 'lrc_url', None):
                setattr(data, 'lrc_url', orig.replace('original.mp3', 'lyrics.lrc'))
        return data

    @field_validator('original_music_link', 'instrumental_music_link', 'cover_url', 'lrc_url', mode='before')
    @classmethod
    def sign_url(cls, v: Optional[str]) -> Optional[str]:
        if v:
            custom_domain_url = v.replace("https://pub-e3eaa10382ee4950bafe2536fdfede82.r2.dev", "https://music.ifreaky.us")
            return generate_signed_url(custom_domain_url)
        return v

    model_config = ConfigDict(from_attributes=True)
