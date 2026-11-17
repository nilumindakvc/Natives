"""Seller-scoped management: storefront, listings, reviews, uploads.

All endpoints require role=seller. Creating/updating listings additionally
requires the seller to be approved by an administrator.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbDep, require_seller
from app.core.config import settings
from app.core.supabase import SupabaseNotConfigured, create_signed_upload_url
from app.models.category import ProductSubCategory, ServiceSubCategory
from app.models.enums import ApprovalStatus, ListingStatus, ListingType
from app.models.listing import Listing
from app.models.review import Review
from app.models.seller import SellerDetail
from app.models.user import User
from app.schemas.common import Message
from app.schemas.interactions import ReviewOut
from app.schemas.listing import ListingCreate, ListingOut, ListingUpdate
from app.schemas.seller import SellerOut, SellerRegister, SellerUpdate
from app.schemas.storage import SignedUploadRequest, SignedUploadResponse

router = APIRouter(prefix="/seller", tags=["seller"])

SellerUser = Depends(require_seller)


def _get_my_seller(user: User, db, require_approved: bool = False) -> SellerDetail:
    seller = db.scalar(select(SellerDetail).where(SellerDetail.user_id == user.id))
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No seller profile. Register with POST /seller/register first.",
        )
    if require_approved and seller.approval_status != ApprovalStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seller account is {seller.approval_status.value}; approval required.",
        )
    return seller


# --------------------------------------------------------------------------- #
# Storefront
# --------------------------------------------------------------------------- #
@router.post("/register", response_model=SellerOut, status_code=status.HTTP_201_CREATED)
def register_seller(payload: SellerRegister, db: DbDep, user: User = SellerUser) -> SellerDetail:
    existing = db.scalar(select(SellerDetail).where(SellerDetail.user_id == user.id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seller profile already exists.")
    seller = SellerDetail(user_id=user.id, **payload.model_dump())
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller


@router.get("/me", response_model=SellerOut)
def get_my_store(db: DbDep, user: User = SellerUser) -> SellerDetail:
    return _get_my_seller(user, db)


@router.patch("/me", response_model=SellerOut)
def update_my_store(payload: SellerUpdate, db: DbDep, user: User = SellerUser) -> SellerDetail:
    seller = _get_my_seller(user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(seller, field, value)
    db.commit()
    db.refresh(seller)
    return seller


# --------------------------------------------------------------------------- #
# Listings
# --------------------------------------------------------------------------- #
def _validate_subcategory(payload_type: ListingType, product_sub_id, service_sub_id, db) -> None:
    if payload_type == ListingType.product:
        sub = db.get(ProductSubCategory, product_sub_id)
        if sub is None or not sub.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product subcategory.")
    else:
        sub = db.get(ServiceSubCategory, service_sub_id)
        if sub is None or not sub.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid service subcategory.")


@router.get("/listings", response_model=list[ListingOut])
def list_my_listings(db: DbDep, user: User = SellerUser) -> list[Listing]:
    seller = _get_my_seller(user, db)
    stmt = select(Listing).where(Listing.seller_id == seller.id).order_by(Listing.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, db: DbDep, user: User = SellerUser) -> Listing:
    seller = _get_my_seller(user, db, require_approved=True)
    _validate_subcategory(payload.listing_type, payload.product_sub_id, payload.service_sub_id, db)
    listing = Listing(seller_id=seller.id, **payload.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.patch("/listings/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: uuid.UUID, payload: ListingUpdate, db: DbDep, user: User = SellerUser
) -> Listing:
    seller = _get_my_seller(user, db, require_approved=True)
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller_id != seller.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

    data = payload.model_dump(exclude_unset=True)
    # Re-validate the subcategory if it changed.
    if "product_sub_id" in data or "service_sub_id" in data:
        product_sub_id = data.get("product_sub_id", listing.product_sub_id)
        service_sub_id = data.get("service_sub_id", listing.service_sub_id)
        _validate_subcategory(listing.listing_type, product_sub_id, service_sub_id, db)

    for field, value in data.items():
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/listings/{listing_id}", response_model=Message)
def delete_listing(listing_id: uuid.UUID, db: DbDep, user: User = SellerUser) -> Message:
    seller = _get_my_seller(user, db)
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller_id != seller.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    db.delete(listing)
    db.commit()
    return Message(detail="Listing deleted.")


# --------------------------------------------------------------------------- #
# Reviews received
# --------------------------------------------------------------------------- #
@router.get("/reviews", response_model=list[ReviewOut])
def my_reviews(db: DbDep, user: User = SellerUser) -> list[Review]:
    seller = _get_my_seller(user, db)
    listing_ids = select(Listing.id).where(Listing.seller_id == seller.id).scalar_subquery()
    stmt = (
        select(Review)
        .where((Review.seller_id == seller.id) | (Review.listing_id.in_(listing_ids)))
        .order_by(Review.created_at.desc())
    )
    return list(db.scalars(stmt).all())


# --------------------------------------------------------------------------- #
# Image uploads (Supabase storage signed URL)
# --------------------------------------------------------------------------- #
@router.post("/uploads/signed-url", response_model=SignedUploadResponse)
def signed_upload_url(payload: SignedUploadRequest, db: DbDep, user: User = SellerUser) -> SignedUploadResponse:
    seller = _get_my_seller(user, db, require_approved=True)
    bucket = settings.avatars_bucket if payload.target == "avatar" else settings.listing_images_bucket
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = f"{seller.id}/{ts}-{uuid.uuid4().hex[:8]}-{payload.filename}"
    try:
        result = create_signed_upload_url(bucket, path)
    except SupabaseNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return SignedUploadResponse(**result)
