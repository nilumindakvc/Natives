"""Enumerated types shared across models and schemas."""
import enum


class UserRole(str, enum.Enum):
    customer = "customer"
    seller = "seller"
    admin = "admin"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ListingType(str, enum.Enum):
    product = "product"
    service = "service"


class ListingKind(str, enum.Enum):
    """Product/service classification from the spec."""
    ready_made = "ready_made"
    made_to_order = "made_to_order"
    batch_production = "batch_production"


class ListingStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    hidden = "hidden"  # hidden by an administrator during moderation
