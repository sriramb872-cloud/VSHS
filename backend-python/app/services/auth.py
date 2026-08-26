# app/services/auth.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.auth import auth_crud
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginRequest, TokenResponse

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, payload: LoginRequest) -> TokenResponse:
        user = auth_crud.get_user_by_mobile(db, mobile_number=payload.mobile)
        
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect mobile number or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if getattr(user, "is_active", None) != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended"
            )
            
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "role": str(user.role),
                "school_id": getattr(user, "school_id", None)
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer"
        )

