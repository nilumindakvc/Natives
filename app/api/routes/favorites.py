"""Customer favourites."""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.api.routes.listings import public_listings_stmt
from app.models.favorite import Favorite
from app.models.listing import Listing
from app.schemas.common import Message
from app.schemas.interactions import FavoriteOut

router = APIRouter(prefix="/me/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteOut])
def list_favorites(user: CurrentUser, db: DbDep) -> list[Favorite]:
    stmt = (
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("/{listing_id}", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
def add_favorite(listing_id: uuid.UUID, user: CurrentUser, db: DbDep) -> Favorite:
    listing = db.scalar(public_listings_stmt().where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

    existing = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id)
    )
    if existing:
        return existing

    fav = Favorite(user_id=user.id, listing_id=listing_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


@router.delete("/{listing_id}", response_model=Message)
def remove_favorite(listing_id: uuid.UUID, user: CurrentUser, db: DbDep) -> Message:
    fav = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id)
    )
    if fav is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in favourites.")
    db.delete(fav)
    db.commit()
    return Message(detail="Removed from favourites.")
