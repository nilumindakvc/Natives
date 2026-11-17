"""Administrator endpoints: user/seller management, approvals, categories,
listing moderation. All endpoints require role=admin."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbDep, PaginationDep, require_admin
from app.models.category import (
    ProductMajorCategory,
    ProductSubCategory,
    ServiceMajorCategory,
    ServiceSubCategory,
)
from app.models.enums import ApprovalStatus, ListingStatus, UserRole
from app.models.listing import Listing
from app.models.seller import SellerDetail
from app.models.user import User
from app.schemas.category import (
    MajorCategoryCreate,
    MajorCategoryOut,
    MajorCategoryUpdate,
    SubCategoryCreate,
    SubCategoryOut,
    SubCategoryUpdate,
)
from app.schemas.common import Message, Page
from app.schemas.listing import ListingOut, ListingStatusUpdate
from app.schemas.seller import SellerAdminOut, SellerRejectRequest
from app.schemas.user import AdminUserUpdate, UserOut
from app.utils import slugify

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

AdminUser = Depends(require_admin)

MAJOR_MODELS = {"product": ProductMajorCategory, "service": ServiceMajorCategory}
SUB_MODELS = {"product": ProductSubCategory, "service": ServiceSubCategory}


def _domain_model(models: dict, domain: str):
    model = models.get(domain)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown category domain.")
    return model


# --------------------------------------------------------------------------- #
# Customer / user accounts
# --------------------------------------------------------------------------- #
@router.get("/users", response_model=Page[UserOut])
def list_users(
    db: DbDep,
    page: PaginationDep,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    q: Optional[str] = Query(default=None, description="Search email / full name"),
) -> Page[UserOut]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: AdminUserUpdate, db: DbDep) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# Seller accounts & approval
# --------------------------------------------------------------------------- #
@router.get("/sellers", response_model=Page[SellerAdminOut])
def list_sellers(
    db: DbDep,
    page: PaginationDep,
    approval_status: Optional[ApprovalStatus] = None,
    q: Optional[str] = Query(default=None, description="Search business name"),
) -> Page[SellerAdminOut]:
    stmt = select(SellerDetail)
    if approval_status:
        stmt = stmt.where(SellerDetail.approval_status == approval_status)
    if q:
        stmt = stmt.where(SellerDetail.business_name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(SellerDetail.created_at.desc()).limit(page.limit).offset(page.offset)
    ).all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)


@router.get("/sellers/{seller_id}", response_model=SellerAdminOut)
def get_seller(seller_id: uuid.UUID, db: DbDep) -> SellerDetail:
    seller = db.get(SellerDetail, seller_id)
    if seller is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")
    return seller


@router.post("/sellers/{seller_id}/approve", response_model=SellerAdminOut)
def approve_seller(seller_id: uuid.UUID, db: DbDep, admin: User = AdminUser) -> SellerDetail:
    seller = db.get(SellerDetail, seller_id)
    if seller is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")
    seller.approval_status = ApprovalStatus.approved
    seller.approved_by = admin.id
    seller.approved_at = datetime.now(timezone.utc)
    seller.rejection_reason = None
    db.commit()
    db.refresh(seller)
    return seller


@router.post("/sellers/{seller_id}/reject", response_model=SellerAdminOut)
def reject_seller(
    seller_id: uuid.UUID, payload: SellerRejectRequest, db: DbDep, admin: User = AdminUser
) -> SellerDetail:
    seller = db.get(SellerDetail, seller_id)
    if seller is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")
    seller.approval_status = ApprovalStatus.rejected
    seller.approved_by = admin.id
    seller.approved_at = datetime.now(timezone.utc)
    seller.rejection_reason = payload.reason
    db.commit()
    db.refresh(seller)
    return seller


# --------------------------------------------------------------------------- #
# Categories (product & service, major & sub)
# --------------------------------------------------------------------------- #
@router.post("/categories/{domain}/major", response_model=MajorCategoryOut, status_code=201)
def create_major(domain: str, payload: MajorCategoryCreate, db: DbDep) -> object:
    model = _domain_model(MAJOR_MODELS, domain)
    data = payload.model_dump()
    data["slug"] = data.get("slug") or slugify(payload.name)
    obj = model(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/categories/{domain}/major/{category_id}", response_model=MajorCategoryOut)
def update_major(domain: str, category_id: uuid.UUID, payload: MajorCategoryUpdate, db: DbDep) -> object:
    model = _domain_model(MAJOR_MODELS, domain)
    obj = db.get(model, category_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/categories/{domain}/major/{category_id}", response_model=Message)
def delete_major(domain: str, category_id: uuid.UUID, db: DbDep) -> Message:
    model = _domain_model(MAJOR_MODELS, domain)
    obj = db.get(model, category_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    db.delete(obj)
    db.commit()
    return Message(detail="Major category deleted.")


@router.post("/categories/{domain}/sub", response_model=SubCategoryOut, status_code=201)
def create_sub(domain: str, payload: SubCategoryCreate, db: DbDep) -> object:
    sub_model = _domain_model(SUB_MODELS, domain)
    major_model = _domain_model(MAJOR_MODELS, domain)
    if db.get(major_model, payload.major_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent major category not found.")
    data = payload.model_dump()
    data["slug"] = data.get("slug") or slugify(payload.name)
    obj = sub_model(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/categories/{domain}/sub/{category_id}", response_model=SubCategoryOut)
def update_sub(domain: str, category_id: uuid.UUID, payload: SubCategoryUpdate, db: DbDep) -> object:
    sub_model = _domain_model(SUB_MODELS, domain)
    obj = db.get(sub_model, category_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("major_id"):
        major_model = _domain_model(MAJOR_MODELS, domain)
        if db.get(major_model, data["major_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent major category not found.")
    for field, value in data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/categories/{domain}/sub/{category_id}", response_model=Message)
def delete_sub(domain: str, category_id: uuid.UUID, db: DbDep) -> Message:
    sub_model = _domain_model(SUB_MODELS, domain)
    obj = db.get(sub_model, category_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    db.delete(obj)
    db.commit()
    return Message(detail="Sub category deleted.")


# --------------------------------------------------------------------------- #
# Listing moderation
# --------------------------------------------------------------------------- #
@router.get("/listings", response_model=Page[ListingOut])
def list_all_listings(
    db: DbDep,
    page: PaginationDep,
    listing_status: Optional[ListingStatus] = None,
    seller_id: Optional[uuid.UUID] = None,
    q: Optional[str] = None,
) -> Page[ListingOut]:
    stmt = select(Listing)
    if listing_status:
        stmt = stmt.where(Listing.status == listing_status)
    if seller_id:
        stmt = stmt.where(Listing.seller_id == seller_id)
    if q:
        stmt = stmt.where(Listing.title.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Listing.created_at.desc()).limit(page.limit).offset(page.offset)
    ).all()
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)


@router.patch("/listings/{listing_id}/status", response_model=ListingOut)
def set_listing_status(listing_id: uuid.UUID, payload: ListingStatusUpdate, db: DbDep) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    listing.status = payload.status
    db.commit()
    db.refresh(listing)
    return listing
