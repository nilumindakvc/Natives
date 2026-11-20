"""Product reviews: create (from a confirmed order), edit/delete own, like
(any customer, toggle), and seller reply.

A customer may review only their own confirmed orders, one review per order.
Public read of a listing's reviews lives in `listings.py`.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbDep, require_seller
from app.core import chat_ops
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.review import Review
from app.models.review_like import ReviewLike
from app.models.user import User
from app.schemas.interactions import ReviewCreate, ReviewOut, ReviewReply, ReviewUpdate

router = APIRouter(prefix="/me/reviews", tags=["reviews"])

SellerUser = Depends(require_seller)


def _to_out(db: Session, review: Review, user_id: Optional[uuid.UUID]) -> ReviewOut:
    out = ReviewOut.model_validate(review)
    if review.seller is not None:
        out.seller_name = review.seller.business_name
        out.seller_avatar_url = review.seller.user.avatar_url if review.seller.user else None
    if user_id is not None:
        liked = db.scalar(
            select(ReviewLike.id).where(
                ReviewLike.review_id == review.id, ReviewLike.user_id == user_id
            )
        )
        out.liked_by_me = liked is not None
    return out


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, user: CurrentUser, db: DbDep) -> ReviewOut:
    order = db.get(Order, payload.order_id)
    if order is None or order.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.status != OrderStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You can review only confirmed orders.",
        )
    if order.listing_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order's product is no longer available.",
        )
    existing = db.scalar(select(Review).where(Review.order_id == order.id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this order.",
        )

    review = Review(
        author_id=user.id,
        listing_id=order.listing_id,
        seller_id=order.seller_id,
        order_id=order.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _to_out(db, review, user.id)


@router.get("", response_model=Optional[ReviewOut])
def get_my_review_for_order(
    user: CurrentUser, db: DbDep, order_id: uuid.UUID = Query(...)
) -> Optional[ReviewOut]:
    review = db.scalar(
        select(Review).where(Review.order_id == order_id, Review.author_id == user.id)
    )
    if review is None:
        return None
    return _to_out(db, review, user.id)


def _own_review(db: Session, review_id: uuid.UUID, user: User) -> Review:
    review = db.get(Review, review_id)
    if review is None or review.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    return review


@router.patch("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: uuid.UUID, payload: ReviewUpdate, user: CurrentUser, db: DbDep
) -> ReviewOut:
    review = _own_review(db, review_id, user)
    if payload.rating is not None:
        review.rating = payload.rating
    if payload.comment is not None:
        review.comment = payload.comment
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return _to_out(db, review, user.id)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: uuid.UUID, user: CurrentUser, db: DbDep) -> None:
    review = _own_review(db, review_id, user)
    db.delete(review)
    db.commit()


@router.post("/{review_id}/like", response_model=ReviewOut)
def toggle_like(review_id: uuid.UUID, user: CurrentUser, db: DbDep) -> ReviewOut:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    existing = db.scalar(
        select(ReviewLike).where(
            ReviewLike.review_id == review_id, ReviewLike.user_id == user.id
        )
    )
    if existing is None:
        db.add(ReviewLike(review_id=review_id, user_id=user.id))
        review.likes_count = (review.likes_count or 0) + 1
    else:
        db.delete(existing)
        review.likes_count = max(0, (review.likes_count or 0) - 1)
    db.commit()
    db.refresh(review)
    return _to_out(db, review, user.id)


@router.post("/{review_id}/reply", response_model=ReviewOut)
def reply_to_review(
    review_id: uuid.UUID, payload: ReviewReply, db: DbDep, user: User = SellerUser
) -> ReviewOut:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    own_seller_id = chat_ops.resolve_seller_id_for_user(db, user.id)
    if own_seller_id is None or review.seller_id != own_seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reply to reviews on your own products.",
        )
    review.seller_reply = payload.reply
    review.seller_reply_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return _to_out(db, review, user.id)
