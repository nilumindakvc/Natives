"""Order request / quote / confirmation schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus
from app.schemas.listing import ListingOut
from app.schemas.seller import SellerOut
from app.schemas.user import UserPublicOut


class OrderCreate(BaseModel):
    listing_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)
    requested_date: Optional[date] = None
    delivery_address: Optional[str] = None
    customization: dict = Field(default_factory=dict)


class OrderQuote(BaseModel):
    """Seller's final details, moving the order from pending -> quoted."""
    final_price: Decimal = Field(ge=0)
    currency: str = Field(default="LKR", max_length=3)
    final_date: Optional[date] = None
    delivery_method: Optional[str] = Field(default=None, max_length=100)
    seller_notes: Optional[str] = None


class OrderSummary(BaseModel):
    """Lightweight order info embedded in a conversation for titling."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_title: str
    status: OrderStatus
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    seller_id: uuid.UUID
    listing_id: Optional[uuid.UUID]
    listing_title: str
    status: OrderStatus
    quantity: int
    requested_date: Optional[date]
    delivery_address: Optional[str]
    customization: dict
    final_price: Optional[Decimal]
    currency: str
    final_date: Optional[date]
    delivery_method: Optional[str]
    seller_notes: Optional[str]
    quoted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    listing: Optional[ListingOut] = None
    customer: Optional[UserPublicOut] = None
    seller: Optional[SellerOut] = None
    conversation_id: Optional[uuid.UUID] = None
