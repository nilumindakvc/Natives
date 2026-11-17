"""Initial phase-1 schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum types (create_type=False -> we create them explicitly below).
user_role = postgresql.ENUM("customer", "seller", "admin", name="user_role", create_type=False)
approval_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="approval_status", create_type=False
)
listing_type = postgresql.ENUM("product", "service", name="listing_type", create_type=False)
listing_kind = postgresql.ENUM(
    "ready_made", "made_to_order", "batch_production", name="listing_kind", create_type=False
)
listing_status = postgresql.ENUM(
    "active", "inactive", "hidden", name="listing_status", create_type=False
)

_ALL_ENUMS = (user_role, approval_status, listing_type, listing_kind, listing_status)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # ------------------------------------------------------------------ users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", user_role, nullable=False, server_default="customer"),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("address", sa.Text()),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ---------------------------------------------------- major category tables
    for tbl in ("product_major_category", "service_major_category"):
        op.create_table(
            tbl,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("slug", sa.String(140), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("image_url", sa.Text()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("slug", name=f"uq_{tbl}_slug"),
        )
        op.create_index(f"ix_{tbl}_slug", tbl, ["slug"])

    # ------------------------------------------------------ sub category tables
    sub_specs = [
        ("product_sub_category", "product_major_category", "uq_product_sub_major_slug"),
        ("service_sub_category", "service_major_category", "uq_service_sub_major_slug"),
    ]
    for tbl, major_tbl, uq_name in sub_specs:
        op.create_table(
            tbl,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("major_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("slug", sa.String(140), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["major_id"], [f"{major_tbl}.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("major_id", "slug", name=uq_name),
        )
        op.create_index(f"ix_{tbl}_major_id", tbl, ["major_id"])
        op.create_index(f"ix_{tbl}_slug", tbl, ["slug"])

    # -------------------------------------------------------------- seller_details
    op.create_table(
        "seller_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("logo_url", sa.Text()),
        sa.Column("banner_url", sa.Text()),
        sa.Column("location", sa.String(255)),
        sa.Column("contact_phone", sa.String(32)),
        sa.Column("approval_status", approval_status, nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_seller_details_user_id"),
    )
    op.create_index("ix_seller_details_user_id", "seller_details", ["user_id"])
    op.create_index("ix_seller_details_approval_status", "seller_details", ["approval_status"])
    op.create_index("ix_seller_details_location", "seller_details", ["location"])

    # --------------------------------------------------------------------- listing
    op.create_table(
        "listing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("listing_type", listing_type, nullable=False),
        sa.Column("listing_kind", listing_kind, nullable=False),
        sa.Column("product_sub_id", postgresql.UUID(as_uuid=True)),
        sa.Column("service_sub_id", postgresql.UUID(as_uuid=True)),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LKR"),
        sa.Column("location", sa.String(255)),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", listing_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["seller_id"], ["seller_details.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_sub_id"], ["product_sub_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_sub_id"], ["service_sub_category.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(listing_type = 'product' AND product_sub_id IS NOT NULL AND service_sub_id IS NULL) "
            "OR (listing_type = 'service' AND service_sub_id IS NOT NULL AND product_sub_id IS NULL)",
            name="ck_listing_category_matches_type",
        ),
    )
    op.create_index("ix_listing_seller_id", "listing", ["seller_id"])
    op.create_index("ix_listing_title", "listing", ["title"])
    op.create_index("ix_listing_listing_type", "listing", ["listing_type"])
    op.create_index("ix_listing_listing_kind", "listing", ["listing_kind"])
    op.create_index("ix_listing_product_sub_id", "listing", ["product_sub_id"])
    op.create_index("ix_listing_service_sub_id", "listing", ["service_sub_id"])
    op.create_index("ix_listing_location", "listing", ["location"])
    op.create_index("ix_listing_status", "listing", ["status"])

    # -------------------------------------------------------------------- favorites
    op.create_table(
        "favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listing.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_favorite_user_listing"),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    op.create_index("ix_favorites_listing_id", "favorites", ["listing_id"])

    # ---------------------------------------------------------------------- follows
    op.create_table(
        "follows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["seller_details.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "seller_id", name="uq_follow_user_seller"),
    )
    op.create_index("ix_follows_user_id", "follows", ["user_id"])
    op.create_index("ix_follows_seller_id", "follows", ["seller_id"])

    # ---------------------------------------------------------------------- reviews
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True)),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True)),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listing.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["seller_details.id"], ondelete="CASCADE"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )
    op.create_index("ix_reviews_author_id", "reviews", ["author_id"])
    op.create_index("ix_reviews_listing_id", "reviews", ["listing_id"])
    op.create_index("ix_reviews_seller_id", "reviews", ["seller_id"])


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("follows")
    op.drop_table("favorites")
    op.drop_table("listing")
    op.drop_table("seller_details")
    op.drop_table("service_sub_category")
    op.drop_table("product_sub_category")
    op.drop_table("service_major_category")
    op.drop_table("product_major_category")
    op.drop_table("users")

    bind = op.get_bind()
    for enum in reversed(_ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
