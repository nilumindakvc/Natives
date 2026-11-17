"""Product and service category tables (major + sub for each)."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.listing import Listing


class ProductMajorCategory(Base, TimestampMixin):
    __tablename__ = "product_major_category"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    subcategories: Mapped[list["ProductSubCategory"]] = relationship(
        back_populates="major", cascade="all, delete-orphan"
    )


class ProductSubCategory(Base, TimestampMixin):
    __tablename__ = "product_sub_category"
    __table_args__ = (UniqueConstraint("major_id", "slug", name="uq_product_sub_major_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    major_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_major_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    major: Mapped["ProductMajorCategory"] = relationship(back_populates="subcategories")
    listings: Mapped[list["Listing"]] = relationship(back_populates="product_sub")


class ServiceMajorCategory(Base, TimestampMixin):
    __tablename__ = "service_major_category"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    subcategories: Mapped[list["ServiceSubCategory"]] = relationship(
        back_populates="major", cascade="all, delete-orphan"
    )


class ServiceSubCategory(Base, TimestampMixin):
    __tablename__ = "service_sub_category"
    __table_args__ = (UniqueConstraint("major_id", "slug", name="uq_service_sub_major_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    major_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_major_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    major: Mapped["ServiceMajorCategory"] = relationship(back_populates="subcategories")
    listings: Mapped[list["Listing"]] = relationship(back_populates="service_sub")
