# backend-python/app/routers/v1/auth.py
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, PasswordChangeRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth_service import authenticate_user, create_user_token
from app.core.security import verify_password, get_password_hash
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_TOKEN_TTL_MINUTES = 30


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, mobile=payload.mobile, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, student ID, employee ID, mobile number, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_user_token(user)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/change-password")
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
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    query = db.query(User)
    user = None
    if payload.mobile:
        user = query.filter(User.mobile == payload.mobile).first()
    elif payload.email:
        user = query.filter(User.email == payload.email).first()

    generic_response = {"message": "If an account exists, a reset token has been issued."}
    if not user:
        return generic_response  # never reveal whether the account exists

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    db.commit()

    # DEV-ONLY: replace with real email/SMS delivery before production.
    generic_response["reset_token"] = token
    generic_response["expires_in_minutes"] = RESET_TOKEN_TTL_MINUTES
    return generic_response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.reset_token).first()
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password_hash = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    return {"message": "Password reset successfully"}
