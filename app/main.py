from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import songs, search, artists, auth, playlists, recommendations, favorites, history, devices, notifications
from app.models.user import User
from app.models.user_session import UserSession
from app.models.playlist import Playlist
from app.models.history import ListeningHistory
from app.models.device_token import DeviceToken
from app.models.notification import Notification

from fastapi.middleware.cors import CORSMiddleware

# Create all database tables (including user_sessions added in Phase 2, and devices/notifications in Phase 4)
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Rate Limiter (slowapi)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title=settings.PROJECT_NAME)

# Enable CORS for browser web applications & local file pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach limiter to app state (required by slowapi)
app.state.limiter = limiter

# Add middleware + error handler
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(songs.router,           prefix="/api/v1/songs",           tags=["Songs"])
app.include_router(search.router,          prefix="/api/v1/search",          tags=["Search"])
app.include_router(artists.router,         prefix="/api/v1/artists",         tags=["Artists"])
app.include_router(auth.router,            prefix="/api/v1/auth",            tags=["Authentication"])
app.include_router(playlists.router,       prefix="/api/v1/playlists",       tags=["Playlists"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(favorites.router,       prefix="/api/v1/favorites",       tags=["Favorites"])
app.include_router(history.router,         prefix="/api/v1/history",         tags=["History"])
app.include_router(devices.router,         prefix="/api/v1/devices",         tags=["Devices"])
app.include_router(notifications.router,   prefix="/api/v1/notifications",   tags=["Notifications"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the HelaGee API — Phase 2"}
