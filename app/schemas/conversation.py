"""Chat conversation / message schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import OrderSummary
from app.schemas.seller import SellerOut
from app.schemas.user import UserPublicOut


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    customer_id: uuid.UUID
    seller_id: uuid.UUID
    listing_id: Optional[uuid.UUID] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    created_at: datetime
    unread_count: int = 0
    seller: Optional[SellerOut] = None
    customer: Optional[UserPublicOut] = None
    order: Optional[OrderSummary] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    created_at: datetime
    read_at: Optional[datetime] = None


# --- Incoming WebSocket payload validation ---------------------------------

class WSSendMessage(BaseModel):
    client_msg_id: Optional[str] = Field(default=None, max_length=64)
    conversation_id: uuid.UUID
    body: str = Field(min_length=1, max_length=2000)


class WSReadReceipt(BaseModel):
    conversation_id: uuid.UUID
    message_ids: list[uuid.UUID]
