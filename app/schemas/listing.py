"""Listing schemas."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ListingKind, ListingStatus, ListingType


class ListingCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    listing_type: ListingType
    listing_kind: ListingKind
    product_sub_id: Optional[uuid.UUID] = None
    service_sub_id: Optional[uuid.UUID] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    currency: str = Field(default="LKR", max_length=3)
    location: Optional[str] = Field(default=None, max_length=255)
    images: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_category(self):
        if self.listing_type == ListingType.product:
            if not self.product_sub_id or self.service_sub_id:
                raise ValueError("product listings require product_sub_id and no service_sub_id")
        else:
            if not self.service_sub_id or self.product_sub_id:
                raise ValueError("service listings require service_sub_id and no product_sub_id")
        return self


class ListingUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    listing_kind: Optional[ListingKind] = None
    product_sub_id: Optional[uuid.UUID] = None
    service_sub_id: Optional[uuid.UUID] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, max_length=3)
    location: Optional[str] = Field(default=None, max_length=255)
    images: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    description: Optional[str]
    listing_type: ListingType
    listing_kind: ListingKind
    product_sub_id: Optional[uuid.UUID]
    service_sub_id: Optional[uuid.UUID]
    price: Optional[Decimal]
    currency: str
    location: Optional[str]
    images: list[str]
    is_active: bool
    status: ListingStatus
    created_at: datetime
    updated_at: datetime


class ListingStatusUpdate(BaseModel):
    status: ListingStatus
