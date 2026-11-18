"""User / profile schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: dict = Field(default_factory=dict)


class UserRegister(BaseModel):
    """Called once after Supabase sign-up to choose a role + set details."""
    role: UserRole = UserRole.customer
    full_name: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    address: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserUpdate(BaseModel):
    """Admin account management."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserPublicOut(BaseModel):
    """Minimal public profile safe to expose to a chat counterparty.

    Deliberately excludes email/phone/address so opening a conversation
    doesn't leak contact details.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
