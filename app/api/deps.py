"""Shared FastAPI dependencies: auth, roles, pagination."""
import uuid
from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenError, decode_access_token
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


CurrentUser = Annotated[User, Depends(get_current_user)]
BootstrapUser = Annotated[User, Depends(get_or_create_user)]


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
