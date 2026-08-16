# 🎵 Geedahara Lyrics & Music API — Developer Reference Guide

Personal reference and cheatsheet for the Geedahara (HelaGee) backend architecture, VPS hosting, database schema, R2 storage structure, and maintenance commands.

---

## 📌 1. Quick Cheatsheet & Endpoints

| Resource | Value / URL |
| :--- | :--- |
| **Live API Docs (Swagger)** | [https://music-api.ifreaky.us/docs](https://music-api.ifreaky.us/docs) |
| **ReDoc** | [https://music-api.ifreaky.us/redoc](https://music-api.ifreaky.us/redoc) |
| **VPS Server IP** | `43.153.207.108` (Tencent Cloud Lighthouse, Ubuntu) |
| **VPS Project Path** | `/var/www/lyrics-api` |
| **Public R2 Custom Domain** | `https://music.ifreaky.us` |
| **GitHub Repo** | `https://github.com/itzMalieth/geedahara-api.git` |

---

## ☁️ 2. Cloudflare R2 Storage Architecture

Each song in R2 (`music` bucket) has a dedicated folder named by its slug/song name:

```text
https://music.ifreaky.us/<Song-Folder-Name>/
├── original.mp3           # Original song audio stream
├── instrumental.mp3       # Karaoke instrumental audio stream
├── cover.jpg              # Album / Artist cover art
├── lyrics.lrc             # Synced karaoke LRC timestamp file ([mm:ss.xx] line)
└── full_lyrics.txt        # Full plain text static lyrics file
```

### URL Signing
Audio and lyrics URLs are signed on-the-fly via HMAC SHA256 (`app/services/url_signer.py`) through Cloudflare Worker so raw bucket files are protected.

---

## 🗄️ 3. Database Schema & Tables (PostgreSQL `songs_db`)

- **`songs`**: `id` (UUID), `song_name`, `artist_name`, `original_music_link`, `instrumental_music_link`, `cover_url`, `r2_lrc_link`, `r2_full_lyrics_link`, `play_count`, `created_at`.
- **`users`**: `id` (UUID), `email`, `firebase_uid`, `google_sub`, `display_name`, `avatar_url`, `created_at`.
- **`user_sessions`**: `id` (UUID), `user_id`, `refresh_token_hash`, `device_info`, `ip_address`, `expires_at`, `revoked`.
- **`playlists`** & **`playlist_songs`**: Custom user playlists and mapped songs.
- **`listening_history`**: Tracks user listening history for recent plays & recommendations.
- **`user_favorites`**: User favorited songs.
- **`device_tokens`**: FCM device tokens for mobile push notifications.
- **`notifications`**: In-app push notification messages.

---

## 🔑 4. Authentication Flow

- **Phase 2 Auth**: Short-lived Access Token (15 minutes) + Long-lived Refresh Token (30 days).
- **Google OAuth**: Mobile app exchanges Google ID token at `/api/v1/auth/google`, backend verifies `google_sub` / `email` and returns JWT pair.
- **Session Tracking**: Refresh tokens are hashed and stored in `user_sessions` for revocation / remote logout.

---

## ⚡ 5. Common VPS & Maintenance Commands

### 🚀 Docker Management
```bash
# Navigate to project
cd /var/www/lyrics-api

# Check running containers
docker compose ps

# View live logs
docker compose logs -f api
docker compose logs -f caddy
docker compose logs -f db
docker compose logs -f meilisearch

# Rebuild and restart all containers
docker compose up -d --build

# Restart only FastAPI backend
docker compose restart api
```

---

### 🔄 Data & Search Index Synchronization
```bash
# 1. Sync missing songs from SQLite (.db) to PostgreSQL
docker exec -it lyrics_api python app/scripts/sync_sqlite_to_postgres.py

# 2. Re-index all PostgreSQL songs & artists into Meilisearch
docker exec -it lyrics_api python app/scripts/sync_db_to_meili.py

# 3. Apply custom SQL migrations
docker exec -it lyrics_api python app/scripts/apply_migrations.py
```

---

### 🐘 Direct PostgreSQL CLI Access
```bash
# Open interactive PostgreSQL shell inside container
docker exec -it lyrics_db psql -U postgres -d songs_db

# Useful SQL queries inside psql:
# \dt                 -> List all tables
# SELECT count(*) FROM songs;
# SELECT count(*) FROM users;
# \q                  -> Exit
```

---

## 🤖 6. CI/CD Auto-Deployment (GitHub Actions)

Pushing to `main` branch automatically triggers `.github/workflows/deploy.yml`:
1. Connects to VPS via SSH (`VPS_HOST`, `VPS_USERNAME`, `VPS_SSH_KEY`).
2. Runs `git pull origin main`.
3. Runs `docker compose up -d --build`.

---

## 🔒 7. Server Ports & Firewall Rules

| Port | Protocol | Purpose | Where Allowed |
| :--- | :--- | :--- | :--- |
| **80** | HTTP | Caddy (HTTP challenge / redirect) | Tencent Cloud Firewall |
| **443** | HTTPS | Caddy (Secure SSL traffic) | Tencent Cloud Firewall |
| **22** | SSH | Linux Remote Login | Tencent Cloud Firewall |
| *8000* | HTTP | FastAPI Internal Container | Docker Network only |
| *5432* | TCP | PostgreSQL Internal Container | Docker Network only |
| *7700* | HTTP | Meilisearch Internal Container | Docker Network only |
