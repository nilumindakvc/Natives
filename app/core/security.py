"""JWT verification for Supabase-issued access tokens.

Supabase now signs user access tokens with **asymmetric** keys (ES256 by
default, shown as "ECC (P-256)" in the dashboard) and publishes the public
signing keys at the project's JWKS endpoint:

    {SUPABASE_URL}/auth/v1/.well-known/jwks.json

We fetch and cache those keys and verify the token signature against them. The
`sub` claim is the Supabase auth user id (uuid) which maps 1:1 to our
`public.users.id`.

Legacy projects that still use a shared HS256 secret can set
JWT_ALGORITHM=HS256 and SUPABASE_JWT_SECRET; that path is handled too.
"""
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import settings


class TokenError(Exception):
    """Raised when a bearer token cannot be verified."""


@lru_cache
def _jwks_client() -> PyJWKClient:
    headers = {}
    if settings.supabase_publishable_key:
        # Some deployments gate the JWKS endpoint behind the apikey header.
        headers["apikey"] = settings.supabase_publishable_key
    return PyJWKClient(settings.jwks_url, headers=headers or None, cache_keys=True)


def _signing_key(token: str):
    if not settings.supabase_url:
        raise TokenError("SUPABASE_URL is not configured on the server.")
    try:
        return _jwks_client().get_signing_key_from_jwt(token).key
    except Exception as exc:  # network / key-not-found / malformed token
        raise TokenError("Unable to resolve token signing key.") from exc


def decode_access_token(token: str) -> dict:
    algorithm = settings.jwt_algorithm.upper()

    if algorithm.startswith("HS"):
        if not settings.supabase_jwt_secret:
            raise TokenError("SUPABASE_JWT_SECRET is not configured on the server.")
        key = settings.supabase_jwt_secret
    else:
        key = _signing_key(token)

    options = {
        "verify_aud": bool(settings.jwt_audience),
        "verify_iss": bool(settings.jwt_verify_issuer),
    }
    decode_kwargs: dict = {"algorithms": [settings.jwt_algorithm], "options": options}
    if settings.jwt_audience:
        decode_kwargs["audience"] = settings.jwt_audience
    if settings.jwt_verify_issuer:
        decode_kwargs["issuer"] = settings.jwt_issuer

    try:
        payload = jwt.decode(token, key, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid authentication token.") from exc
    return payload
