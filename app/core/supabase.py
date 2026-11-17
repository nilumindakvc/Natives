"""Service-role Supabase client for storage and privileged admin operations.

The client is created lazily so the application can boot (and the OpenAPI docs
render) even when Supabase credentials are not yet configured. Any endpoint
that actually needs Supabase will raise a clear error if config is missing.
"""
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.core.config import settings


class SupabaseNotConfigured(RuntimeError):
    pass


@lru_cache
def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise SupabaseNotConfigured(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SECRET_KEY in the environment."
        )
    return create_client(settings.supabase_url, settings.supabase_secret_key)


def create_signed_upload_url(bucket: str, path: str) -> dict[str, Any]:
    """Return a signed URL the client can use to upload a file directly to
    Supabase Storage, plus the public URL the file will have afterwards."""
    client = get_supabase()
    signed = client.storage.from_(bucket).create_signed_upload_url(path)
    public_url = client.storage.from_(bucket).get_public_url(path)
    return {
        "bucket": bucket,
        "path": path,
        "signed_url": signed.get("signed_url") or signed.get("signedUrl"),
        "token": signed.get("token"),
        "public_url": public_url,
    }
