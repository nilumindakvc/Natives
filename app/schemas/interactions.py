"""Schemas for favourites, follows and reviews."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.listing import ListingOut
from app.schemas.seller import SellerOut


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


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    listing_id: Optional[uuid.UUID]
    seller_id: Optional[uuid.UUID]
    rating: int
    comment: Optional[str]
    created_at: datetime
