# backend-python/app/models/password_reset.py
"""Schema for the two password-reset flows.

Flow A - self service (the account has a verified email)
    ``password_reset_otps`` holds ONE row per requested code. Only a keyed hash
    of the 6-digit code is stored, so a database dump cannot be replayed into an
    account takeover. The same row later carries the *hashed*, single-use
    ``reset_token`` handed out after a successful OTP verification, so both
    secrets are short-lived, revocable and never persisted in plain text.

Flow B - admin assisted (no email on file, mainly students)
    ``password_reset_requests`` is the work queue a Principal (their own
    teachers + students) or a Super Admin (everyone) acts on.

Conventions followed from the rest of the schema
-----------------------------------------------
* ``id`` is the plain surrogate primary key (same shape as ``slip_tests``).
* ``status`` is an ``ENUM`` - the same shape ``users.role`` and
  ``slip_tests.status`` already use, so MySQL rejects an unknown lifecycle
  value at the storage layer.
* Timestamps are naive UTC (``datetime.utcnow``), the project-wide convention
  - see ``app/core/time_utils.py``.
* Every column is nullable/defaults explicitly: no implicit state.
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)

from app.core.database import Base


#: Allowed lifecycle values of an admin-assisted request.
PASSWORD_RESET_REQUEST_STATUSES = ("pending", "completed", "rejected")

DEFAULT_REQUEST_STATUS = "pending"


class PasswordResetOtp(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: HMAC-SHA256 of ``user_id:otp`` keyed with SECRET_KEY. Never the code.
    otp_hash = Column(String(128), nullable=False)

    #: Codes are deliberately short-lived (default 10 minutes).
    expires_at = Column(DateTime, nullable=False)

    #: Wrong guesses against THIS code; at OTP_MAX_ATTEMPTS it is dead.
    attempts = Column(Integer, nullable=False, default=0, server_default="0")

    #: Set when the code is consumed (verified, superseded by a resend, or
    #: invalidated by too many wrong attempts).
    used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    #: Source IP of the request that created the code - forensics only.
    request_ip = Column(String(45), nullable=True)

    # --- single-use reset token, issued on successful OTP verification ------
    # Stored as a SHA-256 hash exactly like ``refresh_tokens.token_hash``: the
    # raw token exists only in the response to the caller who proved the OTP.
    reset_token_hash = Column(String(64), nullable=True, index=True)
    reset_token_expires_at = Column(DateTime, nullable=True)


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(*PASSWORD_RESET_REQUEST_STATUSES, name="password_reset_request_status"),
        default=DEFAULT_REQUEST_STATUS,
        server_default=DEFAULT_REQUEST_STATUS,
        nullable=False,
        index=True,
    )

    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    #: Admin who completed/rejected the request (SET NULL when they are gone).
    handled_by = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    handled_at = Column(DateTime, nullable=True)


PasswordResetOtpModel = PasswordResetOtp
PasswordResetRequestModel = PasswordResetRequest
