"""Aggregate all route modules under the API v1 router."""
from fastapi import APIRouter

from app.api.routes import (
    admin,
    categories,
    chat_ws,
    conversations,
    favorites,
    follows,
    listings,
    me,
    orders,
    reviews,
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
api_router.include_router(conversations.router)
api_router.include_router(chat_ws.router)
api_router.include_router(orders.router)
api_router.include_router(reviews.router)
