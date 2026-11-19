"""Orders, per-listing customization fields, and order-scoped conversations.

Revision ID: 0003_orders
Revises: 0002_chat
Create Date: 2026-11-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_orders"
down_revision: Union[str, None] = "0002_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

order_status = postgresql.ENUM("pending", "quoted", "confirmed", name="order_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    order_status.create(bind, checkfirst=True)

    # ----------------------------------------------------------------- orders
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True)),
        sa.Column("listing_title", sa.String(255), nullable=False),
        sa.Column("status", order_status, nullable=False, server_default="pending"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requested_date", sa.Date()),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("customization", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("final_price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LKR"),
        sa.Column("final_date", sa.Date()),
        sa.Column("delivery_method", sa.String(100)),
        sa.Column("seller_notes", sa.Text()),
        sa.Column("quoted_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["seller_details.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listing.id"], ondelete="SET NULL"),
        sa.CheckConstraint("quantity >= 1", name="ck_orders_quantity_positive"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_seller_id", "orders", ["seller_id"])
    op.create_index("ix_orders_listing_id", "orders", ["listing_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # --------------------------------------- listing.customization_fields (new)
    op.add_column(
        "listing",
        sa.Column("customization_fields", postgresql.JSONB(), nullable=False, server_default="[]"),
    )

    # ------------------------------------ conversations become order-scoped
    # Any pre-existing (general) conversations are no longer supported; drop
    # them so order_id can be made NOT NULL. Messages cascade-delete.
    op.add_column("conversations", sa.Column("order_id", postgresql.UUID(as_uuid=True)))
    op.execute("DELETE FROM conversations WHERE order_id IS NULL")
    op.alter_column("conversations", "order_id", nullable=False)
    op.create_foreign_key(
        "fk_conversations_order_id", "conversations", "orders", ["order_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("uq_conversations_customer_seller", "conversations", type_="unique")
    op.create_unique_constraint("uq_conversations_order", "conversations", ["order_id"])
    op.create_index("ix_conversations_order_id", "conversations", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_order_id", table_name="conversations")
    op.drop_constraint("uq_conversations_order", "conversations", type_="unique")
    op.create_unique_constraint(
        "uq_conversations_customer_seller", "conversations", ["customer_id", "seller_id"]
    )
    op.drop_constraint("fk_conversations_order_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "order_id")

    op.drop_column("listing", "customization_fields")

    op.drop_table("orders")

    bind = op.get_bind()
    order_status.drop(bind, checkfirst=True)
