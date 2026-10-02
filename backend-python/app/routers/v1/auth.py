# backend-python/app/routers/v1/auth.py
import secrets
from datetime import datetime, timedelta
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
    ResetPasswordRequest,
    UserResponse,
)
from app.services.auth_service import authenticate_user
from app.core.security import verify_password, get_password_hash
from app.core.token_service import (
    issue_session,
    rotate_session,
    revoke_session,
    revoke_all_sessions,
)
from app.models.user import User
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_TOKEN_TTL_MINUTES = 30


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
@limiter.limit("3/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    query = db.query(User)
    user = None
    if payload.mobile:
        user = query.filter(User.mobile == payload.mobile).first()
    elif payload.email:
        user = query.filter(User.email == payload.email).first()

    # The response must be byte-identical whether or not the account exists -
    # any difference (extra keys, different status) is an account-enumeration
    # oracle usable to verify which mobile numbers/emails are registered.
    generic_response = {
        "message": "If an account exists, a reset token has been issued.",
        "expires_in_minutes": RESET_TOKEN_TTL_MINUTES,
    }
    if not user:
        return generic_response  # never reveal whether the account exists

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    db.commit()

    # No SMS/email provider is configured; an administrator must reset passwords manually.
    return generic_response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.reset_token).first()
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password_hash = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.must_change_password = False
    db.add(user)
    db.commit()

    # A password reset means the credentials may have been compromised:
    # kill every existing session for this account.
    revoke_all_sessions(db, user)
    return {"message": "Password reset successfully"}
