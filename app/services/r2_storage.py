"""
Cloudflare R2 — Production-Ready Upload & URL Retrieval
========================================================
Install:  pip install boto3 python-dotenv
.env:
    R2_ACCOUNT_ID=your_account_id
    R2_ACCESS_KEY_ID=your_access_key_id
    R2_SECRET_ACCESS_KEY=your_secret_access_key
    R2_BUCKET_NAME=your_bucket_name
    R2_BUCKET_TYPE=public   # or: private
    R2_PUBLIC_URL=https://pub-xxxx.r2.dev  # only needed for public buckets / custom domain
"""

from io import BytesIO
import os
import hashlib
import mimetypes
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, find_dotenv

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Walk up directories to find .env (it lives in the project root, not backend/)
_env_path = find_dotenv(usecwd=True)
if not _env_path:
    # Fallback: check parent directory of this script
    _script_parent = Path(__file__).resolve().parent.parent / ".env"
    if _script_parent.exists():
        _env_path = str(_script_parent)
load_dotenv(_env_path or "")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("r2_storage")


# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

class R2Config:
    ACCOUNT_ID        = "fcfbbd925f7d052b914f14a51dc7ac23"
    ACCESS_KEY_ID     = "1f2f66f99caadd6dbfac35173e83c53d"
    SECRET_ACCESS_KEY = "842cf7967513c59cd8554af1d324e10bea027edc80225b8ef2dcee8b4ded78c5"
    BUCKET_NAME       = "music"
    BUCKET_TYPE       = "public"
    PUBLIC_URL        = "https://pub-e3eaa10382ee4950bafe2536fdfede82.r2.dev"
    UPLOAD_RETRIES    = 3
    ENDPOINT_URL      = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"
    PRESIGN_EXPIRY    = 3600


# ──────────────────────────────────────────────
# Client (singleton)
# ──────────────────────────────────────────────

class R2Client:
    _instance: Optional["R2Client"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=R2Config.ENDPOINT_URL,
            aws_access_key_id=R2Config.ACCESS_KEY_ID,
            aws_secret_access_key=R2Config.SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(
                retries={"max_attempts": R2Config.UPLOAD_RETRIES, "mode": "standard"},
                signature_version="s3v4",
            ),
        )
        logger.info(f"Connected to R2 bucket: {R2Config.BUCKET_NAME}")


def _client() -> R2Client:
    return R2Client()


# ──────────────────────────────────────────────
# Upload
# ──────────────────────────────────────────────

def upload_file(
    local_path: str | Path,
    b2_path: Optional[str] = None,
    content_type: Optional[str] = None,
    extra_file_info: Optional[dict] = None,
) -> dict:
    """
    Upload a local file to R2.

    Args:
        local_path:      Path to the local file.
        b2_path:         Destination key in R2 (defaults to filename).
        content_type:    MIME type (auto-detected if omitted).
        extra_file_info: Optional metadata dict (str → str).

    Returns:
        {
            "file_id":    str,
            "file_name":  str,
            "url":        str,
            "size":       int,
            "sha1":       str,
            "content_type": str,
        }
    """
    local_path = Path(local_path)
    if not local_path.is_file():
        raise FileNotFoundError(f"File not found: {local_path}")

    b2_path = b2_path or local_path.name
    content_type = content_type or (
        mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
    )

    sha1 = _sha1(local_path)
    size = local_path.stat().st_size
    client = _client()

    metadata = extra_file_info or {}
    metadata.setdefault("src-last-modified-millis", str(int(local_path.stat().st_mtime * 1000)))

    logger.info(f"Uploading {local_path} -> r2://{R2Config.BUCKET_NAME}/{b2_path}")

    client.s3.upload_file(
        Filename=str(local_path),
        Bucket=R2Config.BUCKET_NAME,
        Key=b2_path,
        ExtraArgs={
            "ContentType": content_type,
            "Metadata": metadata,
        },
    )

    url = _get_download_url(b2_path)
    logger.info(f"Upload complete: {url}")

    return {
        "file_id":      _resolve_file_id(b2_path),
        "file_name":    b2_path,
        "url":          url,
        "size":         size,
        "sha1":         sha1,
        "content_type": content_type,
    }


def upload_fileobj(
    fileobj: BytesIO,
    b2_path: str,
    content_type: str = "application/octet-stream",
    extra_file_info: Optional[dict] = None,
) -> dict:
    """
    Upload a file-like object directly to R2 without loading entire file into memory.
    Useful for streaming large files.
    """
    client = _client()

    fileobj.seek(0, os.SEEK_END)
    size = fileobj.tell()
    fileobj.seek(0)

    sha1_hash = hashlib.sha1()
    for chunk in iter(lambda: fileobj.read(65536), b""):
        sha1_hash.update(chunk)
    sha1 = sha1_hash.hexdigest()
    fileobj.seek(0)

    logger.info(f"Uploading {size} bytes from stream -> r2://{R2Config.BUCKET_NAME}/{b2_path}")

    client.s3.upload_fileobj(
        Fileobj=fileobj,
        Bucket=R2Config.BUCKET_NAME,
        Key=b2_path,
        ExtraArgs={
            "ContentType": content_type,
            "Metadata": extra_file_info or {},
        },
    )

    url = _get_download_url(b2_path)
    logger.info(f"Upload complete: {url}")

    return {
        "file_id":      _resolve_file_id(b2_path),
        "file_name":    b2_path,
        "url":          url,
        "size":         size,
        "sha1":         sha1,
        "content_type": content_type,
    }


def upload_bytes(
    data: bytes,
    b2_path: str,
    content_type: str = "application/octet-stream",
    extra_file_info: Optional[dict] = None,
) -> dict:
    """
    Upload raw bytes (in-memory) directly to R2.

    Returns same shape as upload_file().
    """
    client = _client()
    sha1 = hashlib.sha1(data).hexdigest()

    logger.info(f"Uploading {len(data)} bytes -> r2://{R2Config.BUCKET_NAME}/{b2_path}")

    client.s3.put_object(
        Bucket=R2Config.BUCKET_NAME,
        Key=b2_path,
        Body=data,
        ContentType=content_type,
        Metadata=extra_file_info or {},
    )

    url = _get_download_url(b2_path)
    logger.info(f"Upload complete: {url}")

    return {
        "file_id":      _resolve_file_id(b2_path),
        "file_name":    b2_path,
        "url":          url,
        "size":         len(data),
        "sha1":         sha1,
        "content_type": content_type,
    }


# ──────────────────────────────────────────────
# URL Retrieval
# ──────────────────────────────────────────────

def get_public_url(b2_file_name: str) -> str:
    """
    Return the permanent public download URL for a file.
    Only works when bucket has public access enabled (R2_PUBLIC_URL must be set).
    """
    return _get_download_url(b2_file_name)


def get_presigned_url(
    b2_file_name: str,
    valid_duration_seconds: int = 3600,
    b2_file_id: Optional[str] = None,   # kept for API compatibility; unused in R2
) -> str:
    """
    Generate a time-limited (presigned) download URL for private buckets.

    Args:
        b2_file_name:           The R2 object key / file path.
        valid_duration_seconds: How long the URL is valid (default 1 hour).
        b2_file_id:             Ignored (B2 compat shim — R2 resolves by name).

    Returns:
        Presigned URL string.
    """
    client = _client()

    presigned = client.s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": R2Config.BUCKET_NAME,
            "Key": b2_file_name,
        },
        ExpiresIn=valid_duration_seconds,
    )
    logger.info(f"Presigned URL (valid {valid_duration_seconds}s): {presigned}")
    return presigned


def list_files(prefix: str = "", max_files: int = 100) -> list[dict]:
    """
    List files in the bucket (optionally filtered by prefix).

    Returns list of dicts with file_id, file_name, size, upload_timestamp, url.
    """
    client = _client()
    results = []

    paginator = client.s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=R2Config.BUCKET_NAME,
        Prefix=prefix,
        PaginationConfig={"MaxItems": max_files},
    )

    for page in pages:
        for obj in page.get("Contents", []):
            results.append({
                "file_id":          obj["ETag"].strip('"'),
                "file_name":        obj["Key"],
                "size":             obj["Size"],
                "upload_timestamp": int(obj["LastModified"].timestamp() * 1000),
                "url":              _get_download_url(obj["Key"]),
            })
            if len(results) >= max_files:
                return results

    return results


def delete_file(b2_file_name: str, b2_file_id: Optional[str] = None) -> bool:
    """Delete a file from R2. Returns True on success."""
    client = _client()
    client.s3.delete_object(Bucket=R2Config.BUCKET_NAME, Key=b2_file_name)
    logger.info(f"Deleted: {b2_file_name}")
    return True


# ──────────────────────────────────────────────
# Internals
# ──────────────────────────────────────────────

def _get_download_url(file_name: str) -> str:
    """
    Returns public URL if R2_PUBLIC_URL is configured, otherwise a presigned URL.
    """
    if R2Config.BUCKET_TYPE == "public" and R2Config.PUBLIC_URL:
        return f"{R2Config.PUBLIC_URL}/{file_name}"
    # Fall back to a 7-day presigned URL for private buckets
    return get_presigned_url(file_name, valid_duration_seconds=604800)


def _resolve_file_id(b2_file_name: str) -> str:
    """
    Return the ETag (acts as a file ID) for a given object key.
    """
    client = _client()
    try:
        head = client.s3.head_object(Bucket=R2Config.BUCKET_NAME, Key=b2_file_name)
        return head["ETag"].strip('"')
    except ClientError:
        return ""


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ──────────────────────────────────────────────
# Quick demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json

    # --- Upload a file passed as CLI argument ---
    if len(sys.argv) > 1:
        target = sys.argv[1]
        result = upload_file(target, b2_path=f"uploads/{Path(target).name}")
        print(json.dumps(result, indent=2))

    # --- Upload in-memory bytes ---
    sample_bytes = b"Hello from Cloudflare R2!"
    mem_result = upload_bytes(sample_bytes, "samples/hello.txt", "text/plain")
    print(json.dumps(mem_result, indent=2))

    # --- Public URL ---
    pub = get_public_url("samples/hello.txt")
    print("Public URL:", pub)

    # --- Presigned URL (for private buckets) ---
    pre = get_presigned_url("samples/hello.txt", valid_duration_seconds=1800)
    print("Presigned URL:", pre)

    # --- List files ---
    files = list_files(prefix="samples/", max_files=10)
    for f in files:
        print(f["file_name"], "->", f["url"])