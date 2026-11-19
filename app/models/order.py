"""Customer order requests and the seller quote / customer confirmation flow.

Lifecycle (forward-only, no cancellation yet):
    pending  -> customer requested
    quoted   -> seller provided final price/date/delivery details
    confirmed-> customer confirmed the quote
"""
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.listing import Listing
    from app.models.seller import SellerDetail
    from app.models.user import User


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_orders_quantity_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_details.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listing.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Snapshot so order history stays readable even if the listing is removed.
    listing_title: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"),
        default=OrderStatus.pending,
        server_default=OrderStatus.pending.value,
        nullable=False,
        index=True,
    )

    # --- customer request ---
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    requested_date: Mapped[Optional[date]] = mapped_column(Date)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text)
    customization: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    # --- seller quote ---
    final_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="LKR", server_default="LKR", nullable=False)
    final_date: Mapped[Optional[date]] = mapped_column(Date)
    delivery_method: Mapped[Optional[str]] = mapped_column(String(100))
    seller_notes: Mapped[Optional[str]] = mapped_column(Text)
    quoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    seller: Mapped["SellerDetail"] = relationship(foreign_keys=[seller_id])
    listing: Mapped[Optional["Listing"]] = relationship(foreign_keys=[listing_id])
    conversation: Mapped[Optional["Conversation"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", uselist=False
    )
