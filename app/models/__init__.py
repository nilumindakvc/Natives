"""SQLAlchemy models. Importing this package registers every model on the
shared ``Base.metadata`` (used by Alembic autogenerate and create_all)."""
from app.models.base import Base
from app.models.category import (
    ProductMajorCategory,
    ProductSubCategory,
    ServiceMajorCategory,
    ServiceSubCategory,
)
from app.models.enums import (
    ApprovalStatus,
    ListingKind,
    ListingStatus,
    ListingType,
    UserRole,
)
from app.models.conversation import Conversation
from app.models.favorite import Favorite
from app.models.follow import Follow
from app.models.listing import Listing
from app.models.message import Message
from app.models.review import Review
from app.models.seller import SellerDetail
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "SellerDetail",
    "ProductMajorCategory",
    "ProductSubCategory",
    "ServiceMajorCategory",
    "ServiceSubCategory",
    "Listing",
    "Favorite",
    "Follow",
    "Review",
    "Conversation",
    "Message",
    "UserRole",
    "ApprovalStatus",
    "ListingType",
    "ListingKind",
    "ListingStatus",
]
