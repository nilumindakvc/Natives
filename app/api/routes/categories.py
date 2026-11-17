"""Public category browsing endpoints."""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbDep
from app.models.category import (
    ProductMajorCategory,
    ProductSubCategory,
    ServiceMajorCategory,
    ServiceSubCategory,
)
from app.schemas.category import MajorCategoryOut, SubCategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/products/major", response_model=list[MajorCategoryOut])
def list_product_major(db: DbDep, active_only: bool = True) -> list[ProductMajorCategory]:
    stmt = select(ProductMajorCategory).order_by(ProductMajorCategory.name)
    if active_only:
        stmt = stmt.where(ProductMajorCategory.is_active.is_(True))
    return list(db.scalars(stmt).all())


@router.get("/products/sub", response_model=list[SubCategoryOut])
def list_product_sub(
    db: DbDep,
    major_id: Annotated[Optional[uuid.UUID], Query()] = None,
    active_only: bool = True,
) -> list[ProductSubCategory]:
    stmt = select(ProductSubCategory).order_by(ProductSubCategory.name)
    if major_id:
        stmt = stmt.where(ProductSubCategory.major_id == major_id)
    if active_only:
        stmt = stmt.where(ProductSubCategory.is_active.is_(True))
    return list(db.scalars(stmt).all())


@router.get("/services/major", response_model=list[MajorCategoryOut])
def list_service_major(db: DbDep, active_only: bool = True) -> list[ServiceMajorCategory]:
    stmt = select(ServiceMajorCategory).order_by(ServiceMajorCategory.name)
    if active_only:
        stmt = stmt.where(ServiceMajorCategory.is_active.is_(True))
    return list(db.scalars(stmt).all())


@router.get("/services/sub", response_model=list[SubCategoryOut])
def list_service_sub(
    db: DbDep,
    major_id: Annotated[Optional[uuid.UUID], Query()] = None,
    active_only: bool = True,
) -> list[ServiceSubCategory]:
    stmt = select(ServiceSubCategory).order_by(ServiceSubCategory.name)
    if major_id:
        stmt = stmt.where(ServiceSubCategory.major_id == major_id)
    if active_only:
        stmt = stmt.where(ServiceSubCategory.is_active.is_(True))
    return list(db.scalars(stmt).all())
