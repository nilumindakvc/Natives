"""A persistent 1:1 chat thread between a customer and a seller."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.seller import SellerDetail
    from app.models.user import User


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_conversations_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_details.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listing.id", ondelete="SET NULL"), nullable=True
    )

    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_message_preview: Mapped[Optional[str]] = mapped_column(String(200))

    order: Mapped["Order"] = relationship(back_populates="conversation", foreign_keys=[order_id])
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    seller: Mapped["SellerDetail"] = relationship(foreign_keys=[seller_id])
