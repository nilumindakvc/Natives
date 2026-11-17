"""Public seller (storefront) views."""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbDep, PaginationDep
from app.api.routes.listings import public_listings_stmt
from app.models.enums import ApprovalStatus
from app.models.listing import Listing
from app.models.review import Review
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
def get_seller(seller_id: uuid.UUID, db: DbDep) -> SellerDetail:
    return _get_public_seller(seller_id, db)


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
def get_seller_reviews(seller_id: uuid.UUID, db: DbDep) -> list[Review]:
    _get_public_seller(seller_id, db)
    stmt = select(Review).where(Review.seller_id == seller_id).order_by(Review.created_at.desc())
    return list(db.scalars(stmt).all())
