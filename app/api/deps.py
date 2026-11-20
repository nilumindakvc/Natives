"""Shared FastAPI dependencies: auth, roles, pagination."""
import uuid
from dataclasses import dataclass
from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from supabase_auth.errors import AuthApiError

from app.core.database import get_db
from app.core.security import TokenError, decode_access_token
from app.core.supabase import SupabaseNotConfigured, get_supabase
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token")


@dataclass
class TokenClaims:
    user_id: uuid.UUID
    email: str | None


def get_token_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenClaims:
    """Verify the Supabase JWT and return its claims, without touching the
    database. Used both by `get_current_user` and by the registration
    bootstrap dependency (`get_or_create_user`)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject.")

    try:
        user_id = uuid.UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject.") from exc

    return TokenClaims(user_id=user_id, email=email)


def get_current_user(
    claims: Annotated[TokenClaims, Depends(get_token_claims)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Verify the Supabase JWT and return the matching `users` row.

    Does NOT create a row if one doesn't exist yet — a valid Supabase token
    only proves the person is authenticated with Supabase, not that they
    have finished choosing a role in our app (`POST /me`). Raising 404 here
    lets the client tell "signed in, but not yet registered with us" apart
    from "signed in and ready", which is what drives the mobile app's
    role-selection screen. Only the dedicated `get_or_create_user`
    dependency (used by `POST /me`) is allowed to create the row.
    """
    user = db.get(User, claims.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Call POST /me to complete registration.",
        )
    if claims.email and user.email != claims.email:
        user.email = claims.email
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    return user


def _reclaim_stale_email(db: Session, email: str, new_user_id: uuid.UUID) -> None:
    """Before inserting a new `users` row, check whether another row
    already owns `email` under a different id, and resolve it if so.

    This happens when a Supabase auth user is deleted and a new one is
    created with the same email (e.g. during testing, or once account
    deletion ships): our row from the old identity is orphaned but still
    holds the unique email constraint, which would otherwise crash the
    INSERT below with a raw IntegrityError / 500. We confirm via the
    Supabase admin API whether the old identity truly no longer exists
    (status 404 / user_not_found) before deleting its row — any other
    failure (network blip, misconfiguration, a genuinely different error)
    is left to propagate rather than risk deleting live data on a false
    positive. If the old identity does still exist, this is a real
    collision (e.g. two unlinked identities sharing an email) and we
    surface a clear 409 instead of a 500.
    """
    existing = db.scalar(select(User).where(User.email == email, User.id != new_user_id))
    if existing is None:
        return

    try:
        get_supabase().auth.admin.get_user_by_id(str(existing.id))
    except AuthApiError as exc:
        if exc.status != 404:
            raise
        # Confirmed: the old Supabase identity is gone. Safe to drop the
        # orphaned row and let the caller proceed to create the new one.
        db.delete(existing)
        db.commit()
        return
    except SupabaseNotConfigured:
        # Can't verify either way — don't guess; let the real error surface.
        pass

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="This email is already associated with a different account.",
    )


def get_or_create_user(
    claims: Annotated[TokenClaims, Depends(get_token_claims)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Like `get_current_user`, but creates the row (role defaults to
    customer) on first call. Used only by `POST /me`, which is the one
    endpoint responsible for turning a bare Supabase sign-up into an app
    profile with a chosen role."""
    user = db.get(User, claims.user_id)
    if user is None:
        if claims.email:
            _reclaim_stale_email(db, claims.email, claims.user_id)
        user = User(
            id=claims.user_id,
            email=claims.email or f"{claims.user_id}@users.noemail",
            role=UserRole.customer,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif claims.email and user.email != claims.email:
        user.email = claims.email
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    return user


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Optional[User]:
    """Like `get_current_user`, but returns None instead of raising when the
    caller is anonymous or the token is invalid. Used by public endpoints that
    enrich their response for a signed-in viewer (e.g. `liked_by_me`) without
    requiring auth."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        user_id = uuid.UUID(str(sub))
    except (TokenError, ValueError, TypeError):
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
BootstrapUser = Annotated[User, Depends(get_or_create_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]


def require_role(*roles: UserRole) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(r.value for r in roles)}.",
            )
        return user

    return dependency


# Convenience role guards
require_seller = require_role(UserRole.seller)
require_admin = require_role(UserRole.admin)


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(pagination)]
DbDep = Annotated[Session, Depends(get_db)]
