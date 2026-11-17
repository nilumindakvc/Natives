"""The public users table (shared by customers, sellers and admins).

`id` equals the Supabase `auth.users.id` (uuid). Authentication data itself
lives in Supabase; this table holds role and common profile details.
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.favorite import Favorite
    from app.models.follow import Follow
    from app.models.review import Review
    from app.models.seller import SellerDetail


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        default=UserRole.customer,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    address: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    seller_detail: Mapped[Optional["SellerDetail"]] = relationship(
        back_populates="user",
        foreign_keys="SellerDetail.user_id",
        uselist=False,
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    follows: Mapped[list["Follow"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
