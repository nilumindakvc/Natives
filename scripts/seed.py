"""Seed starter data for phase 1.

Run from the backend/ directory (with the DB migrated):

    python -m scripts.seed

What it does (idempotent):
  * Inserts a starter set of product & service categories (major + sub),
    derived from the categories listed in the project spec. Existing rows
    (matched by slug) are left untouched.
  * Promotes the user whose email equals BOOTSTRAP_ADMIN_EMAIL to role=admin,
    if such a user already exists (the user must have signed up via Supabase
    first so the row exists).
"""
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.category import (
    ProductMajorCategory,
    ProductSubCategory,
    ServiceMajorCategory,
    ServiceSubCategory,
)
from app.models.enums import UserRole
from app.models.user import User
from app.utils import slugify

# (major name, [sub names])
PRODUCT_CATEGORIES = {
    "Food & Confectionery": ["Cakes", "Sweets", "Preserved Food", "Fresh Fruits"],
    "Textiles & Clothing": ["Sarees", "Batik", "Curtains", "Pillow Covers"],
    "Natural Fibre Goods": ["Bags", "Footwear", "Hats"],
    "Home & Kitchenware": ["Coconut Products", "Clay Cookware", "Pottery & Ceramics"],
    "Art & Decor": ["Paintings (Portraits)", "Wooden Sculptures", "Flowers"],
    "Handmade Crafts": ["Handmade Jewelry", "Greeting Cards", "Creative Items"],
    "Wellness": ["Ayurveda Products"],
}

SERVICE_CATEGORIES = {
    "Events & Decoration": ["Traditional Decoration", "Modern Decoration"],
    "Photography & Video": ["Photography", "Videography"],
    "Beauty & Bridal": ["Bridal Dressing", "Makeup"],
}


def _seed_categories(db, major_model, sub_model, data: dict) -> int:
    created = 0
    for major_name, sub_names in data.items():
        major_slug = slugify(major_name)
        major = db.scalar(select(major_model).where(major_model.slug == major_slug))
        if major is None:
            major = major_model(name=major_name, slug=major_slug, is_active=True)
            db.add(major)
            db.flush()  # assign id
            created += 1
        for sub_name in sub_names:
            sub_slug = slugify(sub_name)
            exists = db.scalar(
                select(sub_model).where(
                    sub_model.major_id == major.id, sub_model.slug == sub_slug
                )
            )
            if exists is None:
                db.add(
                    sub_model(major_id=major.id, name=sub_name, slug=sub_slug, is_active=True)
                )
                created += 1
    return created


def seed() -> None:
    db = SessionLocal()
    try:
        created = 0
        created += _seed_categories(
            db, ProductMajorCategory, ProductSubCategory, PRODUCT_CATEGORIES
        )
        created += _seed_categories(
            db, ServiceMajorCategory, ServiceSubCategory, SERVICE_CATEGORIES
        )
        db.commit()
        print(f"Categories: {created} new row(s) inserted.")

        email = settings.bootstrap_admin_email.strip()
        if email:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                print(
                    f"Bootstrap admin '{email}' not found. Have them sign up via "
                    "Supabase and call GET /api/v1/me once, then re-run this script."
                )
            else:
                user.role = UserRole.admin
                db.commit()
                print(f"Promoted '{email}' to admin.")
        else:
            print("BOOTSTRAP_ADMIN_EMAIL not set; skipping admin promotion.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
