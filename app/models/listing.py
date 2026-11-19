"""Unified listing table for both products and services.

A listing links to exactly one of product_sub_id / service_sub_id depending on
listing_type (enforced at the application layer and by a DB check constraint).
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ListingKind, ListingStatus, ListingType

if TYPE_CHECKING:
    from app.models.category import ProductSubCategory, ServiceSubCategory
    from app.models.review import Review
    from app.models.seller import SellerDetail


class Listing(Base, TimestampMixin):
    __tablename__ = "listing"
    __table_args__ = (
        CheckConstraint(
            "(listing_type = 'product' AND product_sub_id IS NOT NULL AND service_sub_id IS NULL) "
            "OR (listing_type = 'service' AND service_sub_id IS NOT NULL AND product_sub_id IS NULL)",
            name="ck_listing_category_matches_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seller_details.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    listing_type: Mapped[ListingType] = mapped_column(
        SAEnum(ListingType, name="listing_type"), nullable=False, index=True
    )
    listing_kind: Mapped[ListingKind] = mapped_column(
        SAEnum(ListingKind, name="listing_kind"), nullable=False, index=True
    )

    product_sub_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_sub_category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    service_sub_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_sub_category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="LKR", server_default="LKR", nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    images: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # Seller-defined customization inputs for order requests:
    # a list of {key, label, type, required} the order form renders.
    customization_fields: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    status: Mapped[ListingStatus] = mapped_column(
        SAEnum(ListingStatus, name="listing_status"),
        default=ListingStatus.active,
        server_default=ListingStatus.active.value,
        nullable=False,
        index=True,
    )

    seller: Mapped["SellerDetail"] = relationship(back_populates="listings")
    product_sub: Mapped[Optional["ProductSubCategory"]] = relationship(back_populates="listings")
    service_sub: Mapped[Optional["ServiceSubCategory"]] = relationship(back_populates="listings")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
