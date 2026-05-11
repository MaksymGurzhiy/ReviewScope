"""
Supabase Storage helpers.

Files are organised inside the `reviews` bucket as:
    <user_id>/<analysis_id>/<filename>

Each user can only see their own folder (enforced by RLS in 001_initial_schema.sql).
"""
import logging
import mimetypes
import tempfile
from pathlib import Path
from typing import BinaryIO

from src.config import settings
from src.database.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


def _content_type(filename: str) -> str:
    mt, _ = mimetypes.guess_type(filename)
    return mt or "application/octet-stream"


def upload_review_file(
    user_id: str,
    analysis_id: str,
    filename: str,
    file_bytes: bytes,
) -> str:
    """Upload bytes to Supabase Storage. Returns the storage path."""
    sb = get_supabase_admin()
    path = f"{user_id}/{analysis_id}/{filename}"
    sb.storage.from_(settings.storage_bucket).upload(
        path=path,
        file=file_bytes,
        file_options={
            "content-type": _content_type(filename),
            "upsert": "true",
        },
    )
    logger.info("Uploaded to storage: %s (%d bytes)", path, len(file_bytes))
    return path


def download_review_file(path: str) -> bytes:
    sb = get_supabase_admin()
    return sb.storage.from_(settings.storage_bucket).download(path)


def download_to_tempfile(path: str) -> Path:
    """Download a file from storage to a local temporary path. Caller is responsible for deletion."""
    data = download_review_file(path)
    suffix = Path(path).suffix
    tmp = tempfile.NamedTemporaryFile(prefix="rs_", suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()


def delete_review_file(path: str) -> None:
    sb = get_supabase_admin()
    try:
        sb.storage.from_(settings.storage_bucket).remove([path])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete %s from storage: %s", path, exc)


def create_signed_download_url(path: str, expires_in_seconds: int = 3600) -> str:
    sb = get_supabase_admin()
    res = (
        sb.storage.from_(settings.storage_bucket)
        .create_signed_url(path, expires_in_seconds)
    )
    return res.get("signedURL") or res.get("signed_url") or ""
