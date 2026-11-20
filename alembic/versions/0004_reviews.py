"""Product reviews: order link, likes, seller replies, and the review_likes table.

Revision ID: 0004_reviews
Revises: 0003_orders
Create Date: 2026-11-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_reviews"
down_revision: Union[str, None] = "0003_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------- reviews: new columns
    op.add_column("reviews", sa.Column("order_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_reviews_order_id", "reviews", "orders", ["order_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint("uq_reviews_order", "reviews", ["order_id"])
    op.create_index("ix_reviews_order_id", "reviews", ["order_id"])
    op.add_column(
        "reviews", sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("reviews", sa.Column("seller_reply", sa.Text()))
    op.add_column("reviews", sa.Column("seller_reply_at", sa.DateTime(timezone=True)))
    op.add_column("reviews", sa.Column("updated_at", sa.DateTime(timezone=True)))

    # ----------------------------------------------------------- review_likes
    op.create_table(
        "review_likes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("review_id", "user_id", name="uq_review_like_user"),
    )
    op.create_index("ix_review_likes_review_id", "review_likes", ["review_id"])
    op.create_index("ix_review_likes_user_id", "review_likes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_review_likes_user_id", table_name="review_likes")
    op.drop_index("ix_review_likes_review_id", table_name="review_likes")
    op.drop_table("review_likes")

    op.drop_column("reviews", "updated_at")
    op.drop_column("reviews", "seller_reply_at")
    op.drop_column("reviews", "seller_reply")
    op.drop_column("reviews", "likes_count")
    op.drop_index("ix_reviews_order_id", table_name="reviews")
    op.drop_constraint("uq_reviews_order", "reviews", type_="unique")
    op.drop_constraint("fk_reviews_order_id", "reviews", type_="foreignkey")
    op.drop_column("reviews", "order_id")
