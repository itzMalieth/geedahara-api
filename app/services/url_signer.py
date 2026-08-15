import hmac
import hashlib
import time
from urllib.parse import urlparse, urlencode
from app.core.config import settings

def generate_signed_url(base_url: str, expires_in_seconds: int = 3600) -> str:
    """
    Takes a public Cloudflare URL (e.g. https://music.ifreaky.us/originals/song.mp3)
    and turns it into a signed URL using HMAC-SHA256.
    """
    if not base_url:
        return base_url
        
    # 1. Calculate expiration timestamp
    expires = int(time.time()) + expires_in_seconds
    
    # 2. Extract the path (e.g. /originals/song.mp3)
    parsed = urlparse(base_url)
    path = parsed.path
    
    # 3. Create the string to sign: "/path?expires=1234567890"
    string_to_sign = f"{path}?expires={expires}"
    
    # 4. Generate HMAC-SHA256 signature
    secret_bytes = settings.URL_SIGNING_SECRET.encode('utf-8')
    message_bytes = string_to_sign.encode('utf-8')
    
    signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).hexdigest()
    
    # 5. Construct the final URL
    query_params = {
        "expires": expires,
        "signature": signature
    }
    
    # Reconstruct the URL with the new query parameters
    final_url = f"{parsed.scheme}://{parsed.netloc}{path}?{urlencode(query_params)}"
    
    return final_url
