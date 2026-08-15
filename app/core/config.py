from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lyrics API"
    DATABASE_URL: str = "postgresql://postgres:admin@localhost:5432/songs_db"
    
    # R2 configuration
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "music"
    R2_PUBLIC_URL: str = ""

    # Meilisearch configuration
    MEILI_URL: str = "http://127.0.0.1:7700"
    MEILI_MASTER_KEY: str = "aSampleMasterKey"

    # URL Signing (Cloudflare Worker)
    URL_SIGNING_SECRET: str = "super_secret_key_change_me_in_production"

    # Authentication (JWT & Google)
    JWT_SECRET_KEY: str = "jwt_super_secret_key_change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # Phase 2: short-lived access token + long-lived refresh token
    ACCESS_TOKEN_EXPIRY_MINUTES: int = 15             # 15 minutes
    REFRESH_TOKEN_EXPIRY_DAYS: int = 30               # 30 days

    # Legacy — kept for backwards compat, not used in Phase 2
    JWT_EXPIRATION_HOURS: int = 24

    GOOGLE_CLIENT_ID: str = "204996929096-65pcnife9nta3b7elat7hm7kvotf5j78.apps.googleusercontent.com"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
