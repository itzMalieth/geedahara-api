# Geedahara Lyrics & Music API 🎵

High-performance, containerized backend API for the Geedahara (HelaGee) Music & Lyrics streaming platform. Built with FastAPI, PostgreSQL, Meilisearch, Cloudflare R2, and Caddy.

---

## 🚀 Features

- **FastAPI Core**: Async RESTful API with automated interactive OpenAPI/Swagger docs.
- **Instant Search Engine**: Powered by Meilisearch for typo-tolerant song and artist search.
- **Dual-Mode Lyrics Support**:
  - Synced Karaoke (`.lrc` format)
  - Full Plain Text Lyrics (`full_lyrics.txt`)
- **Cloudflare R2 URL Signing**: Signed URL generation for secure audio/media streaming.
- **Authentication**: JWT access/refresh token system with Google OAuth integration.
- **User Features**: Playlists, favorites, listening history, and device tokens for FCM push notifications.
- **Reverse Proxy & SSL**: Caddy auto-provisions and renews Let's Encrypt SSL certificates.
- **Dockerized Architecture**: Pre-configured with memory limits optimized for 2GB VPS hosting.

---

## 🛠️ Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Search Engine**: [Meilisearch](https://www.meilisearch.com/)
- **Reverse Proxy / TLS**: [Caddy](https://caddyserver.com/)
- **Object Storage**: Cloudflare R2 (S3-compatible)
- **Deployment**: Docker Compose & GitHub Actions CI/CD

---

## 📁 Project Structure

```text
lyrics-api/
├── app/
│   ├── api/v1/          # API route handlers (songs, search, auth, playlists, etc.)
│   ├── core/            # App config, database session & security
│   ├── models/          # SQLAlchemy DB models
│   ├── schemas/         # Pydantic schemas / request & response validation
│   ├── services/        # Business logic, search sync, URL signing & notifications
│   └── scripts/         # DB migrations and Meilisearch sync scripts
├── credentials/         # Firebase service account & secrets (git-ignored)
├── Caddyfile            # Reverse proxy & HTTPS domain configuration
├── docker-compose.yml   # Multi-container orchestration (api, db, meilisearch, caddy)
├── Dockerfile           # FastAPI container image build definition
└── requirements.txt     # Python dependencies
```

---

## ⚙️ Environment Configuration

Create a `.env` file based on `.env.example`:

```env
DOMAIN=music-api.ifreaky.us
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=songs_db
DATABASE_URL=postgresql://postgres:your_secure_password@db:5432/songs_db
MEILI_MASTER_KEY=your_meili_master_key
MEILI_URL=http://meilisearch:7700
URL_SIGNING_SECRET=your_signing_secret
JWT_SECRET_KEY=your_jwt_secret
```

---

## 🐳 Running with Docker

### 1. Build and Start All Services
```bash
docker compose up -d --build
```

### 2. Check Service Logs
```bash
docker compose logs -f api
docker compose logs -f caddy
```

### 3. Sync Database & Meilisearch Index
```bash
# Sync SQLite songs to PostgreSQL
docker exec -it lyrics_api python app/scripts/sync_sqlite_to_postgres.py

# Sync PostgreSQL songs and artists to Meilisearch
docker exec -it lyrics_api python app/scripts/sync_db_to_meili.py
```

---

## 📖 API Documentation

Once the server is running, visit:
- **Swagger UI**: `https://<YOUR_DOMAIN>/docs`
- **ReDoc**: `https://<YOUR_DOMAIN>/redoc`
