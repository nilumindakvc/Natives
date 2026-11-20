"""Current-user profile endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import BootstrapUser, CurrentUser, DbDep
from app.core.config import settings
from app.core.supabase import SupabaseNotConfigured, create_signed_upload_url
from app.models.enums import UserRole
from app.schemas.storage import SignedUploadRequest, SignedUploadResponse
from app.schemas.user import UserOut, UserRegister, UserUpdate

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=UserOut)
def get_me(user: CurrentUser) -> UserOut:
    """Return the current user's profile.

    404s if the person is authenticated with Supabase but hasn't finished
    registering with us yet (never called POST /me) — the client uses that
    to show the role-selection screen rather than assuming "customer".
    """
    return user


@router.post("", response_model=UserOut)
def register_profile(payload: UserRegister, user: BootstrapUser, db: DbDep) -> UserOut:
    """Set the account role (customer or seller) and initial profile details.

    Called once right after Supabase sign-up — creates the profile row if it
    doesn't exist yet. Does not allow self-promotion to admin.
    """
    role = UserRole(payload.role)
    if role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role cannot be self-assigned.",
        )
    user.role = role
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.address is not None:
        user.address = payload.address
    db.commit()
    db.refresh(user)
    return user


@router.patch("", response_model=UserOut)
def update_me(payload: UserUpdate, user: CurrentUser, db: DbDep) -> UserOut:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/avatar/signed-url", response_model=SignedUploadResponse)
def avatar_signed_url(payload: SignedUploadRequest, user: CurrentUser) -> SignedUploadResponse:
    """A signed upload URL for the current user's profile image, usable by any
    authenticated user (customer or seller). Always targets the avatars bucket,
    namespaced by the user's id."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = f"{user.id}/{ts}-{uuid.uuid4().hex[:8]}-{payload.filename}"
    try:
        result = create_signed_upload_url(settings.avatars_bucket, path)
    except SupabaseNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return SignedUploadResponse(**result)
