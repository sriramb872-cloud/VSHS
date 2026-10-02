# backend-python/app/core/token_service.py
"""Access + refresh token session model.

Architecture:

* **Access token** - short-lived JWT (default 30 min) held by the client.
  Carries the user's ``tv`` (token version) claim; the server rejects any
  token whose claim no longer matches ``users.token_version``.
* **Refresh token** - opaque random string (default 14 days) stored server
  side as a SHA-256 hash. Presented to ``POST /auth/refresh`` to obtain a
  fresh access token; every refresh *rotates* it, so a replayed/stolen
  refresh token stops working as soon as the legitimate client refreshes.
* **Revocation** - per session (logout), per user (logout-all, password
  change/reset, admin revoke). Bumping ``users.token_version`` additionally
  invalidates every outstanding *access* token immediately.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


class RefreshTokenError(HTTPException):
    """401 raised for any invalid/expired/revoked refresh token."""

    def __init__(self, detail: str = "Invalid or expired refresh token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_access_token(user: User) -> str:
    return create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "school_id": user.school_id,
            "tv": int(user.token_version or 0),
        }
    )


def issue_session(db: Session, user: User) -> dict:
    """Issue a new access token + refresh token pair for ``user``."""
    access_token = _issue_access_token(user)

    raw_refresh = secrets.token_urlsafe(48)
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        token_version=int(user.token_version or 0),
        expires_at=datetime.utcnow()
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_row)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "must_change_password": bool(getattr(user, "must_change_password", False)),
    }


def _load_active_refresh_token(db: Session, raw_token: str) -> RefreshToken:
    if not raw_token:
        raise RefreshTokenError()
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .first()
    )
    if row is None or row.revoked_at is not None:
        raise RefreshTokenError()
    if row.expires_at <= datetime.utcnow():
        raise RefreshTokenError("Refresh token has expired")
    return row


def rotate_session(db: Session, raw_token: str) -> dict:
    """Validate a refresh token, revoke it, and issue a fresh token pair.

    The presented token is revoked *before* the new pair is issued, so
    replaying the same refresh token (a classic token-theft signal) fails.
    """
    row = _load_active_refresh_token(db, raw_token)

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        row.revoked_at = datetime.utcnow()
        db.commit()
        raise RefreshTokenError()

    account_status = getattr(user, "is_active", "ACTIVE")
    if account_status != "ACTIVE":
        raise RefreshTokenError("User account is not active")

    if int(row.token_version or 0) != int(user.token_version or 0):
        # The session was globally invalidated after this token was issued
        # (password change, logout-all, admin revoke).
        row.revoked_at = datetime.utcnow()
        db.commit()
        raise RefreshTokenError()

    row.revoked_at = datetime.utcnow()
    row.last_used_at = datetime.utcnow()
    db.flush()

    new_pair = issue_session(db, user)
    row.replaced_by_id = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(new_pair["refresh_token"]))
        .first()
        .id
    )
    db.commit()
    return new_pair


def revoke_session(db: Session, raw_token: Optional[str]) -> bool:
    """Revoke one refresh token (logout). Idempotent; True if one was revoked."""
    if not raw_token:
        return False
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .first()
    )
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.utcnow()
    db.commit()
    return True


def revoke_all_sessions(db: Session, user: User) -> int:
    """Revoke every refresh token of ``user`` AND invalidate all outstanding
    access tokens by incrementing the token version.

    Used by: password change, password reset, logout-all, and admin-initiated
    session invalidation. Returns the number of refresh tokens revoked.
    """
    now = datetime.utcnow()
    revoked = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .update({RefreshToken.revoked_at: now}, synchronize_session=False)
    )
    user.token_version = int(user.token_version or 0) + 1
    db.add(user)
    db.commit()
    return revoked
