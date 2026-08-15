"""
Session Cleanup Script (Phase 3)

This script connects to the HelaGee database and deletes `user_sessions`
that are either expired or revoked.
This should be run periodically (e.g., via cron) to keep the DB small.

Usage:
    python scripts/cleanup_sessions.py
"""

import sys
import os
from datetime import datetime, timezone

# Add the 'app' directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.models.user_session import UserSession

def run_cleanup():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    
    try:
        # Delete sessions where expires_at < now OR revoked_at < now
        deleted = db.query(UserSession).filter(
            (UserSession.expires_at < now) | (UserSession.revoked_at < now)
        ).delete()
        
        db.commit()
        print(f"[{now.isoformat()}] Session cleanup successful. Deleted {deleted} expired/revoked session(s).")
    except Exception as e:
        db.rollback()
        print(f"[{now.isoformat()}] Session cleanup failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_cleanup()
