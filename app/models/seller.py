"""Seller business details / digital storefront."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ApprovalStatus

if TYPE_CHECKING:
    from app.models.listing import Listing
    from app.models.user import User


class SellerDetail(Base, TimestampMixin):
    __tablename__ = "seller_details"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    banner_url: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32))

    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.pending,
        server_default=ApprovalStatus.pending.value,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(
        back_populates="seller_detail", foreign_keys=[user_id]
    )
    listings: Mapped[list["Listing"]] = relationship(
        back_populates="seller", cascade="all, delete-orphan"
    )
