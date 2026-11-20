"""Reviews left by customers on products they have a confirmed order for.

A review targets a listing (and its seller) and is tied to the confirmed
order it came from — one review per order (``uq_reviews_order``). Likes are
tracked individually in ``review_likes`` and denormalised onto
``likes_count``; a seller may reply once, stored inline on the row.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.listing import Listing
    from app.models.order import Order
    from app.models.review_like import ReviewLike
    from app.models.seller import SellerDetail
    from app.models.user import User


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        UniqueConstraint("order_id", name="uq_reviews_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listing.id", ondelete="CASCADE"), index=True
    )
    seller_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_details.id", ondelete="CASCADE"), index=True
    )
    # The confirmed order this review came from. Nullable for legacy (phase-1)
    # rows; new reviews always set it, and the unique constraint enforces one
    # review per order.
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    seller_reply: Mapped[Optional[str]] = mapped_column(Text)
    seller_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    author: Mapped["User"] = relationship(back_populates="reviews")
    listing: Mapped[Optional["Listing"]] = relationship(back_populates="reviews")
    seller: Mapped[Optional["SellerDetail"]] = relationship()
    order: Mapped[Optional["Order"]] = relationship()
    likes: Mapped[list["ReviewLike"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
