# backend-python/app/routers/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    PasswordChangeResponse,
    PasswordChangeRequest,
    ForgotPasswordRequest,
    VerifyResetOtpRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.auth_service import authenticate_user
from app.services.password_reset import (
    PasswordResetError,
    generic_response,
    reset_password as perform_password_reset,
    start_reset,
    verify_otp,
)
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.core.token_service import (
    issue_session,
    rotate_session,
    revoke_session,
    revoke_all_sessions,
)
from app.models.user import User
from app.core.rate_limit import client_ip_key, limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _reset_error(exc: PasswordResetError) -> HTTPException:
    """Uniform error shape for the reset endpoints.

    ``detail`` is always ``{"message": ..., "code": ...}`` so the client can
    branch on a stable code instead of matching on prose.
    """
    return HTTPException(
        status_code=exc.status_code,
        detail={"message": exc.detail, "code": exc.code},
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, mobile=payload.mobile, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, student ID, employee ID, mobile number, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return issue_session(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access + refresh token pair.

    The presented refresh token is revoked (rotated) as part of the exchange,
    so replaying an old one fails with 401.
    """
    return rotate_session(db, payload.refresh_token)


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    """Revoke the caller's refresh token. Idempotent: unknown/expired tokens
    still return 200 so clients can always clear their local state."""
    revoke_session(db, payload.refresh_token)
    return {"message": "Logged out"}


@router.post("/logout-all")
def logout_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Invalidate every session of the current user: revokes all refresh
    tokens and bumps the token version, which instantly invalidates every
    outstanding access token (including the one used for this request)."""
    revoked = revoke_all_sessions(db, current_user)
    return {"message": "Logged out of all sessions", "sessions_revoked": revoked}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/change-password", response_model=PasswordChangeResponse)
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()

    # Invalidate every previously issued session (access + refresh tokens),
    # then hand this client a fresh pair so the current flow can continue.
    revoke_all_sessions(db, current_user)
    session = issue_session(db, current_user)
    return {"message": "Password changed successfully", **session}


@router.post("/forgot-password")
@limiter.limit("5/hour", key_func=client_ip_key)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Step 1 of self-service recovery.

    ALWAYS answers with the same generic message - for an unknown login ID, a
    deactivated account, an account with no email and an account whose code was
    just sent. Anything else would turn this endpoint into an oracle for
    "which login IDs are registered".

    What happens behind that response:
      * account with a verified email -> 6-digit code (stored only as a keyed
        HMAC, 10 minutes, 5 attempts) delivered over SMTP;
      * account without an email (or whose mail fails) -> queued as an
        admin-assisted reset request for the Principal / Super Admin;
      * over the per-login-ID cap -> nothing is sent, response unchanged.

    Rate limits: 5/hour per IP (slowapi, 429) and 5/hour per login ID
    (database count, silently enforced).
    """
    start_reset(db, payload.login_id, request_ip=client_ip_key(request))
    return generic_response()


@router.post("/verify-reset-otp")
@limiter.limit("60/hour", key_func=client_ip_key)
def verify_reset_otp(
    request: Request,
    payload: VerifyResetOtpRequest,
    db: Session = Depends(get_db),
):
    """Step 2: exchange the emailed code for a short-lived, single-use token.

    The reset token is returned ONLY here - to a caller who just proved they
    control the account. It is stored server-side as a SHA-256 hash, lives for
    10 minutes and can be spent exactly once.

    Failures (stable ``code``): ``INVALID_OTP`` (unknown login ID, wrong code),
    ``OTP_EXPIRED``, ``OTP_LOCKED`` (5 wrong attempts), ``ADMIN_RESET_REQUIRED``
    (no deliverable email - the account needs a staff-issued temporary
    password).
    """
    try:
        _user, reset_token = verify_otp(db, payload.login_id, payload.otp)
    except PasswordResetError as exc:
        raise _reset_error(exc) from None
    return {
        "message": "Code verified.",
        "reset_token": reset_token,
        "expires_in_minutes": settings.RESET_TOKEN_TTL_MINUTES,
    }


@router.post("/reset-password")
@limiter.limit("30/hour", key_func=client_ip_key)
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Step 3: spend the reset token and set a new password.

    Enforces the password policy (8+ chars, upper, lower, digit; shipped
    defaults and the current password rejected), burns the token so it cannot
    be replayed, revokes every existing session of the account and writes an
    audit log entry.
    """
    try:
        perform_password_reset(db, payload.reset_token, payload.new_password)
    except PasswordResetError as exc:
        raise _reset_error(exc) from None
    return {"message": "Password reset successfully"}
