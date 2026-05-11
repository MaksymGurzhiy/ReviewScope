"""
Supabase JWT verification & FastAPI auth dependencies.

Supabase issues access tokens signed with an asymmetric key (ES256). The
public keys are published via JWKS at:
    {SUPABASE_URL}/auth/v1/.well-known/jwks.json

For backwards compatibility we also support the legacy HS256 JWT secret
(stored in SUPABASE_JWT_SECRET).
"""
import logging
import time
from typing import Optional

import urllib.request
import json

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import settings

logger = logging.getLogger(__name__)


class CurrentUser(BaseModel):
    id: str
    email: Optional[str] = None
    role: str = "authenticated"
    raw_token: str


# ---------------- JWKS cache ----------------
_JWKS_CACHE: dict = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600  # 1 hour


def _fetch_jwks() -> list:
    """Download JWKS from Supabase Auth, cached for 1 hour."""
    now = time.time()
    if _JWKS_CACHE["keys"] is not None and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    if not settings.supabase_url:
        return []

    url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = json.loads(resp.read())
        keys = body.get("keys", [])
        _JWKS_CACHE["keys"] = keys
        _JWKS_CACHE["fetched_at"] = now
        return keys
    except Exception as exc:
        logger.warning("Failed to fetch JWKS from %s: %s", url, exc)
        return _JWKS_CACHE["keys"] or []


def _key_for_token(token: str) -> Optional[dict]:
    """Pick the JWK whose `kid` matches the token header."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        return None
    kid = header.get("kid")
    keys = _fetch_jwks()
    if not kid:
        return keys[0] if keys else None
    for k in keys:
        if k.get("kid") == kid:
            return k
    return None


def _decode_token(token: str) -> dict:
    """Try ES256/RS256 via JWKS first, fall back to legacy HS256 secret."""
    decode_options = {"verify_aud": False}

    jwk = _key_for_token(token)
    if jwk is not None:
        alg = jwk.get("alg", "ES256")
        try:
            return jwt.decode(token, jwk, algorithms=[alg], options=decode_options)
        except JWTError as exc:
            logger.debug("JWKS verification failed: %s", exc)

    if settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options=decode_options,
            )
        except JWTError as exc:
            logger.warning("HS256 verification failed: %s", exc)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    claims = _decode_token(token)

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a subject (sub).",
        )

    return CurrentUser(
        id=user_id,
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
        raw_token=token,
    )


def get_optional_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Optional[CurrentUser]:
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization)
    except HTTPException:
        return None


CurrentUserDep = Depends(get_current_user)
OptionalUserDep = Depends(get_optional_user)
