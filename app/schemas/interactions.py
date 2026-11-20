"""Schemas for favourites, follows and reviews."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.listing import ListingOut
from app.schemas.seller import SellerOut
from app.schemas.user import UserPublicOut


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    created_at: datetime
    listing: Optional[ListingOut] = None


class FollowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    created_at: datetime
    seller: Optional[SellerOut] = None


class ReviewCreate(BaseModel):
    """A customer reviews one of their confirmed orders."""
    order_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewReply(BaseModel):
    """A seller's reply to a review on their product."""
    reply: str = Field(min_length=1)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    listing_id: Optional[uuid.UUID]
    seller_id: Optional[uuid.UUID]
    order_id: Optional[uuid.UUID] = None
    rating: int
    comment: Optional[str]
    likes_count: int = 0
    liked_by_me: bool = False
    seller_reply: Optional[str] = None
    seller_reply_at: Optional[datetime] = None
    seller_name: Optional[str] = None
    seller_avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: Optional[UserPublicOut] = None
