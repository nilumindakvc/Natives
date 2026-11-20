"""Public listing discovery and detail."""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import DbDep, OptionalUser, PaginationDep
from app.models.enums import ApprovalStatus, ListingKind, ListingStatus, ListingType
from app.models.listing import Listing
from app.models.review import Review
from app.models.review_like import ReviewLike
from app.models.seller import SellerDetail
from app.schemas.common import Page
from app.schemas.interactions import ReviewOut
from app.schemas.listing import ListingOut

router = APIRouter(prefix="/listings", tags=["listings"])


def public_listings_stmt() -> Select:
    """Only active listings from approved sellers are publicly visible."""
    return (
        select(Listing)
        .join(SellerDetail, Listing.seller_id == SellerDetail.id)
        .where(
            Listing.is_active.is_(True),
            Listing.status == ListingStatus.active,
            SellerDetail.approval_status == ApprovalStatus.approved,
        )
    )


@router.get("", response_model=Page[ListingOut])
def search_listings(
    db: DbDep,
    page: PaginationDep,
    q: Annotated[Optional[str], Query(description="Free-text search on title/description")] = None,
    listing_type: Optional[ListingType] = None,
    listing_kind: Optional[ListingKind] = None,
    product_sub_id: Optional[uuid.UUID] = None,
    service_sub_id: Optional[uuid.UUID] = None,
    location: Optional[str] = None,
    seller_id: Optional[uuid.UUID] = None,
) -> Page[ListingOut]:
    stmt = public_listings_stmt()

    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if listing_type:
        stmt = stmt.where(Listing.listing_type == listing_type)
    if listing_kind:
        stmt = stmt.where(Listing.listing_kind == listing_kind)
    if product_sub_id:
        stmt = stmt.where(Listing.product_sub_id == product_sub_id)
    if service_sub_id:
        stmt = stmt.where(Listing.service_sub_id == service_sub_id)
    if location:
        stmt = stmt.where(Listing.location.ilike(f"%{location}%"))
    if seller_id:
        stmt = stmt.where(Listing.seller_id == seller_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Listing.created_at.desc()).limit(page.limit).offset(page.offset)
    ).all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: uuid.UUID, db: DbDep) -> Listing:
    listing = db.scalar(public_listings_stmt().where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    return listing


@router.get("/{listing_id}/reviews", response_model=list[ReviewOut])
def get_listing_reviews(listing_id: uuid.UUID, db: DbDep, user: OptionalUser) -> list[ReviewOut]:
    exists = db.scalar(public_listings_stmt().where(Listing.id == listing_id))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    reviews = list(
        db.scalars(
            select(Review)
            .options(joinedload(Review.author), joinedload(Review.seller).joinedload(SellerDetail.user))
            .where(Review.listing_id == listing_id)
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
        if r.seller is not None:
            item.seller_name = r.seller.business_name
            item.seller_avatar_url = r.seller.user.avatar_url if r.seller.user else None
        out.append(item)
    return out
