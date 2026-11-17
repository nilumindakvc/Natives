"""Aggregate all route modules under the API v1 router."""
from fastapi import APIRouter

from app.api.routes import (
    admin,
    categories,
    favorites,
    follows,
    listings,
    me,
    seller,
    sellers,
)

api_router = APIRouter()
api_router.include_router(me.router)
api_router.include_router(categories.router)
api_router.include_router(listings.router)
api_router.include_router(sellers.router)
api_router.include_router(favorites.router)
api_router.include_router(follows.router)
api_router.include_router(seller.router)
api_router.include_router(admin.router)
