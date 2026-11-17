"""Customers following sellers."""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.enums import ApprovalStatus
from app.models.follow import Follow
from app.models.seller import SellerDetail
from app.schemas.common import Message
from app.schemas.interactions import FollowOut

router = APIRouter(prefix="/me/follows", tags=["follows"])


@router.get("", response_model=list[FollowOut])
def list_follows(user: CurrentUser, db: DbDep) -> list[Follow]:
    stmt = select(Follow).where(Follow.user_id == user.id).order_by(Follow.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("/{seller_id}", response_model=FollowOut, status_code=status.HTTP_201_CREATED)
def follow_seller(seller_id: uuid.UUID, user: CurrentUser, db: DbDep) -> Follow:
    seller = db.get(SellerDetail, seller_id)
    if seller is None or seller.approval_status != ApprovalStatus.approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")

    existing = db.scalar(
        select(Follow).where(Follow.user_id == user.id, Follow.seller_id == seller_id)
    )
    if existing:
        return existing

    follow = Follow(user_id=user.id, seller_id=seller_id)
    db.add(follow)
    db.commit()
    db.refresh(follow)
    return follow


@router.delete("/{seller_id}", response_model=Message)
def unfollow_seller(seller_id: uuid.UUID, user: CurrentUser, db: DbDep) -> Message:
    follow = db.scalar(
        select(Follow).where(Follow.user_id == user.id, Follow.seller_id == seller_id)
    )
    if follow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not following this seller.")
    db.delete(follow)
    db.commit()
    return Message(detail="Unfollowed seller.")
