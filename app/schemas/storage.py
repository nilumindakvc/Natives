"""Storage (signed upload URL) schemas."""
from typing import Optional

from pydantic import BaseModel, Field


class SignedUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    # "listing" (default) or "avatar" -> maps to the configured buckets
    target: str = Field(default="listing")


class SignedUploadResponse(BaseModel):
    bucket: str
    path: str
    signed_url: Optional[str]
    token: Optional[str]
    public_url: Optional[str]
