"""Seller detail / storefront schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalStatus


class SellerRegister(BaseModel):
    business_name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=32)


class SellerUpdate(BaseModel):
    business_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=32)


class SellerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    description: Optional[str]
    logo_url: Optional[str]
    banner_url: Optional[str]
    location: Optional[str]
    contact_phone: Optional[str]
    approval_status: ApprovalStatus
    created_at: datetime
    updated_at: datetime


class SellerAdminOut(SellerOut):
    """Includes moderation fields only admins should see."""
    rejection_reason: Optional[str]
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]


class SellerRejectRequest(BaseModel):
    reason: Optional[str] = None
