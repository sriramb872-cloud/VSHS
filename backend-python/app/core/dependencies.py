# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = verify_access_token(token)
        if not payload:
            raise credentials_exception
        user_identifier = payload.get("sub") or payload.get("user_id")
        if user_identifier is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user = None
    if isinstance(user_identifier, int) or (isinstance(user_identifier, str) and user_identifier.isdigit()):
        user = db.query(User).filter(User.id == int(user_identifier)).first()
    else:
        user = db.query(User).filter((User.email == user_identifier) | (User.mobile == user_identifier)).first()

    if user is None:
        raise credentials_exception
        
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive or suspended account"
        )
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

def require_roles(*allowed_roles: str):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_role = str(getattr(current_user, "role", ""))
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for this role"
            )
        return current_user
    return role_checker


