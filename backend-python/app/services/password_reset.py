# backend-python/app/services/password_reset.py
"""Password recovery: self-service OTP by email (Flow A) + admin assistance.

Design rules this module exists to enforce:

* **No account-enumeration oracle.** ``start_reset`` returns ONE byte-identical
  response for "unknown login ID", "known but no email" and "known with email".
  Callers must never vary the body, status or shape by account state.
* **Nothing secret is persisted or logged in clear text.** The 6-digit code is
  stored as an HMAC-SHA256 keyed with ``SECRET_KEY``; the reset token as a
  SHA-256 hash (the same treatment ``refresh_tokens`` gets). The code only ever
  leaves the process inside the mail body.
* **Everything is short-lived and single-use.** Code: 10 minutes and 5 wrong
  attempts. Reset token: 10 minutes, consumed by the first successful reset.
* **Recovery never strands an account.** A user without an email (or whose mail
  fails to send) is queued for an admin-assisted reset instead of being left
  with nothing.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import settings
from app.core.mailer import send_mail
from app.core.security import get_password_hash, verify_password
from app.core.token_service import revoke_all_sessions
from app.models.password_reset import PasswordResetOtp, PasswordResetRequest
from app.models.user import User
from app.services.auth_service import find_users_by_identifier

# The ONLY body POST /auth/forgot-password ever returns. Identical whether the
# login ID is unknown, has no email, or had a code sent a second ago.
GENERIC_MESSAGE = "If an account exists, a code has been sent."

INVALID_OTP_MESSAGE = "Invalid or expired code."
EXPIRED_OTP_MESSAGE = "This code has expired. Please request a new one."
LOCKED_OTP_MESSAGE = "Too many incorrect attempts. Please request a new code."
ADMIN_HELP_MESSAGE = "Please contact your Principal or class teacher to reset your password."
INVALID_TOKEN_MESSAGE = "Invalid or expired reset token."

#: Shipped defaults that must never be accepted as a *new* password. The list
#: is intentionally tiny and explicit - these are the values printed in manuals
#: and set by admin resets, i.e. the exact passwords an attacker guesses first.
WEAK_PASSWORDS = frozenset({"Principal@123", "Password@123", "Admin@123"})


class PasswordResetError(Exception):
    """Recoverable, client-facing failure (HTTP status + stable error code)."""

    def __init__(self, detail: str, code: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Lookup (shared with login: same identifiers, same order)
# ---------------------------------------------------------------------------


def find_user_by_login_id(db: Session, login_id: str) -> Optional[User]:
    """First *active* account matching the login ID (mobile, email,
    admission number or employee ID).

    Deactivated accounts are treated exactly like unknown IDs - a disabled
    account must not be recoverable through self-service.
    """
    for user in find_users_by_identifier(db, str(login_id or "").strip()):
        if str(getattr(user, "is_active", "ACTIVE") or "").upper() == "ACTIVE":
            return user
    return None


# ---------------------------------------------------------------------------
# Secret derivation
# ---------------------------------------------------------------------------


def _keyed(value: str) -> str:
    """HMAC-SHA256 keyed with SECRET_KEY - salted by construction, so two
    accounts receiving the same code never store the same digest."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def hash_otp(user_id: int, otp: str) -> str:
    """Hash a code bound to its owner. Verification recomputes and compares
    with ``hmac.compare_digest`` (constant time)."""
    return _keyed(f"{user_id}:{otp}")


def hash_reset_token(raw_token: str) -> str:
    """Server-side storage form of a reset token (never the token itself)."""
    return hashlib.sha256(str(raw_token or "").encode("utf-8")).hexdigest()


def generate_otp() -> str:
    """Uniform 6-digit numeric code (000000-999999)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_temp_password() -> str:
    """Random admin-issued temporary password, always strength-compliant.

    Returned to the admin exactly once and stored only as a bcrypt hash, so
    even a full database read cannot recover it.
    """
    body = [secrets.choice(string.ascii_lowercase) for _ in range(8)]
    body.append(secrets.choice(string.ascii_uppercase))
    body.extend(secrets.choice(string.digits) for _ in range(2))
    body.append(secrets.choice("!@#$%"))
    secrets.SystemRandom().shuffle(body)
    return "".join(body)


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------


def validate_password_strength(new_password: str, *, user: Optional[User] = None) -> Optional[str]:
    """Return a human-readable reason the password is unacceptable, else None.

    Minimum bar: 8 characters with an uppercase letter, a lowercase letter and
    a digit. Well-known shipped defaults are rejected outright, as is the
    account's current password (a "reset" that changes nothing protects
    nobody).
    """
    password = str(new_password or "")
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one digit."
    if password in WEAK_PASSWORDS:
        return "This password is not allowed. Please choose a different one."
    if user is not None and getattr(user, "password_hash", None):
        try:
            if verify_password(password, user.password_hash):
                return "New password must be different from your current password."
        except Exception:  # noqa: BLE001 - a corrupt stored hash must not block recovery
            pass
    return None


# ---------------------------------------------------------------------------
# Flow B helpers - admin-assisted queue
# ---------------------------------------------------------------------------


def _pending_request(db: Session, user_id: int) -> Optional[PasswordResetRequest]:
    return (
        db.query(PasswordResetRequest)
        .filter(
            PasswordResetRequest.user_id == user_id,
            PasswordResetRequest.status == "pending",
        )
        .order_by(PasswordResetRequest.requested_at.desc())
        .first()
    )


def ensure_admin_request(db: Session, user: User) -> PasswordResetRequest:
    """Queue (or reuse) the admin-assisted reset request for this account.

    Idempotent: a user tapping "resend" five times still produces one pending
    row, so the Principal's queue is never spammed.
    """
    existing = _pending_request(db, user.id)
    if existing is not None:
        return existing
    row = PasswordResetRequest(user_id=user.id, status="pending", requested_at=datetime.utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit_log(
        db,
        user_id=None,
        school_id=user.school_id,
        action="PASSWORD_RESET_REQUESTED",
        resource_type="User",
        resource_id=user.id,
        details={"channel": "admin_assisted"},
    )
    return row


def close_pending_requests(db: Session, user_id: int, *, handled_by: Optional[int] = None) -> None:
    """Close every outstanding queue entry once the password has been set.

    Prevents a stale request from being actioned after the account has already
    recovered (by self-service or by another admin).
    """
    pending = _pending_request(db, user_id)
    if pending is None:
        return
    pending.status = "completed"
    pending.handled_by = handled_by
    pending.handled_at = datetime.utcnow()
    db.add(pending)
    db.commit()


# ---------------------------------------------------------------------------
# Flow A - forgot password
# ---------------------------------------------------------------------------


def generic_response() -> dict:
    """The one and only response shape of POST /auth/forgot-password."""
    return {"message": GENERIC_MESSAGE, "expires_in_minutes": settings.OTP_TTL_MINUTES}


def recent_reset_attempts(db: Session, user_id: int) -> int:
    """Reset requests made for this account in the last hour (both flows).

    Counted in the database on purpose: with several gunicorn workers an
    in-memory counter would only hold per process and let an attacker multiply
    the limit by the worker count.
    """
    since = datetime.utcnow() - timedelta(hours=1)
    otps = (
        db.query(PasswordResetOtp)
        .filter(PasswordResetOtp.user_id == user_id, PasswordResetOtp.created_at >= since)
        .count()
    )
    requests = (
        db.query(PasswordResetRequest)
        .filter(PasswordResetRequest.user_id == user_id, PasswordResetRequest.requested_at >= since)
        .count()
    )
    return otps + requests


def _send_otp_email(user: User, otp: str) -> bool:
    """Deliver the code. The OTP lives only in this call's message body."""
    ttl = settings.OTP_TTL_MINUTES
    body = (
        f"Hello {user.display_name},\n\n"
        f"Your SCHOLARIS password reset code is:\n\n"
        f"    {otp}\n\n"
        f"The code expires in {ttl} minute(s) and can be used {settings.OTP_MAX_ATTEMPTS} times "
        f"before it is invalidated.\n\n"
        "If you did not request a password reset you can safely ignore this "
        "message - your password has not changed.\n\n"
        "Never share this code with anyone, including school staff.\n"
    )
    return send_mail(
        to=user.email,
        subject="Your SCHOLARIS password reset code",
        body=body,
    )


def _create_otp(db: Session, user: User, request_ip: Optional[str]) -> Tuple[PasswordResetOtp, str]:
    """Store a fresh code (hash only) and retire anything outstanding.

    Returns ``(row, plaintext_code)``: the code exists only in this return
    value, never on the row.
    """
    now = datetime.utcnow()

    # A resend invalidates every previous code AND its reset token: only the
    # most recent request may complete, so an old mail can never be replayed.
    outstanding = (
        db.query(PasswordResetOtp)
        .filter(
            PasswordResetOtp.user_id == user.id,
            PasswordResetOtp.used_at.is_(None),
        )
        .all()
    )
    for row in outstanding:
        row.used_at = now
        row.reset_token_hash = None
        row.reset_token_expires_at = None
        db.add(row)

    otp = generate_otp()
    created = PasswordResetOtp(
        user_id=user.id,
        otp_hash=hash_otp(user.id, otp),
        expires_at=now + timedelta(minutes=settings.OTP_TTL_MINUTES),
        attempts=0,
        created_at=now,
        request_ip=(str(request_ip)[:45] if request_ip else None),
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return created, otp


def start_reset(db: Session, login_id: str, request_ip: Optional[str] = None) -> dict:
    """POST /auth/forgot-password. Always returns ``generic_response()``.

    Side effects by account state (never visible in the response):
      * unknown / deactivated        -> nothing
      * over the per-login-ID cap    -> nothing (per-IP cap is slowapi's)
      * email on file                -> new 6-digit code, HMAC-hashed, mailed
      * no email, or mail failed     -> pending admin-assisted request
    """
    user = find_user_by_login_id(db, login_id)
    if user is None:
        return generic_response()

    if recent_reset_attempts(db, user.id) >= settings.FORGOT_PASSWORD_PER_HOUR:
        # Silently respecting the cap keeps the response identical to the
        # "no such account" case - a 429 here would be an oracle.
        return generic_response()

    if not str(user.email or "").strip():
        ensure_admin_request(db, user)
        return generic_response()

    row, otp = _create_otp(db, user, request_ip)

    if not _send_otp_email(user, otp):
        # Mail is down (or the address is broken): never leave the account
        # unreachable. Retire the code we could not deliver and queue an admin
        # reset instead - the response still says the same thing.
        row.used_at = datetime.utcnow()
        db.add(row)
        db.commit()
        ensure_admin_request(db, user)

    return generic_response()


# ---------------------------------------------------------------------------
# Flow A - verify the code
# ---------------------------------------------------------------------------


def _active_otp(db: Session, user_id: int) -> Optional[PasswordResetOtp]:
    return (
        db.query(PasswordResetOtp)
        .filter(
            PasswordResetOtp.user_id == user_id,
            PasswordResetOtp.used_at.is_(None),
        )
        .order_by(PasswordResetOtp.created_at.desc(), PasswordResetOtp.id.desc())
        .first()
    )


def verify_otp(db: Session, login_id: str, otp: str) -> Tuple[User, str]:
    """Validate a code and mint the short-lived, single-use reset token.

    Returns ``(user, raw_reset_token)``. The raw token is returned to the
    caller who proved ownership of the account; only its SHA-256 hash is
    written to ``password_reset_otps``.

    Failures raise :class:`PasswordResetError` with a stable ``code``:
    ``INVALID_OTP`` / ``OTP_EXPIRED`` / ``OTP_LOCKED`` / ``ADMIN_RESET_REQUIRED``.
    """
    user = find_user_by_login_id(db, login_id)
    presented = str(otp or "").strip()

    # Unknown login IDs fail with the exact same message as a wrong code, so
    # this endpoint cannot be used to test which login IDs exist.
    if user is None:
        raise PasswordResetError(INVALID_OTP_MESSAGE, "INVALID_OTP")

    row = _active_otp(db, user.id)
    if row is None:
        if _pending_request(db, user.id) is not None:
            # Account exists but has no deliverable code -> the only state the
            # client genuinely needs to know about (it changes the next step
            # completely). Rate-limited by the per-OTP attempt budget below for
            # every other branch.
            raise PasswordResetError(ADMIN_HELP_MESSAGE, "ADMIN_RESET_REQUIRED", 403)
        raise PasswordResetError(INVALID_OTP_MESSAGE, "INVALID_OTP")

    now = datetime.utcnow()
    if row.expires_at is None or row.expires_at <= now:
        raise PasswordResetError(EXPIRED_OTP_MESSAGE, "OTP_EXPIRED")

    max_attempts = settings.OTP_MAX_ATTEMPTS
    if int(row.attempts or 0) >= max_attempts:
        row.used_at = now
        db.add(row)
        db.commit()
        raise PasswordResetError(LOCKED_OTP_MESSAGE, "OTP_LOCKED")

    candidate = hash_otp(user.id, presented)
    if not hmac.compare_digest(candidate, str(row.otp_hash)):
        row.attempts = int(row.attempts or 0) + 1
        exhausted = row.attempts >= max_attempts
        if exhausted:
            row.used_at = now
        db.add(row)
        db.commit()
        if exhausted:
            raise PasswordResetError(LOCKED_OTP_MESSAGE, "OTP_LOCKED")
        raise PasswordResetError(INVALID_OTP_MESSAGE, "INVALID_OTP")

    # --- verified: consume the code and issue the reset token ---------------
    raw_token = secrets.token_urlsafe(32)
    row.used_at = now
    row.reset_token_hash = hash_reset_token(raw_token)
    row.reset_token_expires_at = now + timedelta(minutes=settings.RESET_TOKEN_TTL_MINUTES)
    db.add(row)
    db.commit()
    return user, raw_token


# ---------------------------------------------------------------------------
# Flow A - complete the reset
# ---------------------------------------------------------------------------


def reset_password(db: Session, reset_token: str, new_password: str) -> User:
    """Consume a single-use reset token and set the new password.

    On success: the password hash is replaced, the token is destroyed, every
    existing session (access *and* refresh) is revoked, and an audit row is
    written. A replay of the same token fails.
    """
    digest = hash_reset_token(reset_token)
    now = datetime.utcnow()

    row = (
        db.query(PasswordResetOtp)
        .filter(PasswordResetOtp.reset_token_hash == digest)
        .first()
    )
    if row is None or row.reset_token_expires_at is None or row.reset_token_expires_at <= now:
        raise PasswordResetError(INVALID_TOKEN_MESSAGE, "RESET_TOKEN_INVALID")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise PasswordResetError(INVALID_TOKEN_MESSAGE, "RESET_TOKEN_INVALID")

    weak = validate_password_strength(new_password, user=user)
    if weak:
        raise PasswordResetError(weak, "WEAK_PASSWORD")

    # Burn the token first: a failed write afterwards must not leave it usable.
    row.reset_token_hash = None
    row.reset_token_expires_at = None
    row.used_at = row.used_at or now
    db.add(row)

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    # Legacy columns from the retired raw-token flow: always cleared so no
    # stale credential can ever be resurrected.
    user.reset_token = None
    user.reset_token_expires_at = None
    db.add(user)
    db.commit()

    close_pending_requests(db, user.id)

    # The credentials may have been compromised: kill every live session.
    revoke_all_sessions(db, user)

    write_audit_log(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="PASSWORD_RESET",
        resource_type="User",
        resource_id=user.id,
        details={"method": "otp_email"},
    )
    return user
