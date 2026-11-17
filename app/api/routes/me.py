"""Current-user profile endpoints."""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import BootstrapUser, CurrentUser, DbDep
from app.models.enums import UserRole
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
