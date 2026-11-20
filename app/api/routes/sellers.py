"""Public seller (storefront) views."""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbDep, OptionalUser, PaginationDep
from app.api.routes.listings import public_listings_stmt
from app.models.enums import ApprovalStatus
from app.models.listing import Listing
from app.models.review import Review
from app.models.review_like import ReviewLike
from app.models.seller import SellerDetail
from app.schemas.common import Page
from app.schemas.interactions import ReviewOut
from app.schemas.listing import ListingOut
from app.schemas.seller import SellerOut

router = APIRouter(prefix="/sellers", tags=["sellers"])


def _get_public_seller(seller_id: uuid.UUID, db) -> SellerDetail:
    seller = db.get(SellerDetail, seller_id)
    if seller is None or seller.approval_status != ApprovalStatus.approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")
    return seller


@router.get("/{seller_id}", response_model=SellerOut)
def get_seller(seller_id: uuid.UUID, db: DbDep) -> SellerOut:
    seller = _get_public_seller(seller_id, db)
    out = SellerOut.model_validate(seller)
    out.avatar_url = seller.user.avatar_url if seller.user else None
    return out


@router.get("/{seller_id}/listings", response_model=Page[ListingOut])
def get_seller_listings(seller_id: uuid.UUID, db: DbDep, page: PaginationDep) -> Page[ListingOut]:
    _get_public_seller(seller_id, db)
    stmt = public_listings_stmt().where(Listing.seller_id == seller_id)
    from sqlalchemy import func

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Listing.created_at.desc()).limit(page.limit).offset(page.offset)
    ).all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)


@router.get("/{seller_id}/reviews", response_model=list[ReviewOut])
def get_seller_reviews(seller_id: uuid.UUID, db: DbDep, user: OptionalUser) -> list[ReviewOut]:
    _get_public_seller(seller_id, db)
    reviews = list(
        db.scalars(
            select(Review)
            .options(joinedload(Review.author))
            .where(Review.seller_id == seller_id)
            .order_by(Review.created_at.desc())
        ).all()
    )

    liked_ids: set[uuid.UUID] = set()
    if user is not None and reviews:
        liked_ids = set(
            db.scalars(
                select(ReviewLike.review_id).where(
                    ReviewLike.user_id == user.id,
                    ReviewLike.review_id.in_([r.id for r in reviews]),
                )
            ).all()
        )

    out: list[ReviewOut] = []
    for r in reviews:
        item = ReviewOut.model_validate(r)
        item.liked_by_me = r.id in liked_ids
        out.append(item)
    return out
