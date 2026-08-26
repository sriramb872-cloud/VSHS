# backend-python/app/routers/v1/users.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user, require_roles
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


def serialize_user(u: User) -> dict:
    school_name = None
    school_code = None
    if getattr(u, "school", None):
        school_name = getattr(u.school, "name", None) or getattr(u.school, "school_name", None)
        school_code = getattr(u.school, "code", None) or getattr(u.school, "school_code", None)

    return {
        "id": u.id,
        "school_id": u.school_id,
        "school_name": school_name,
        "school_code": school_code,
        "mobile": u.mobile,
        "email": u.email,
        "display_name": u.display_name,
        "full_name": u.display_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
    }


@router.get("", response_model=List[dict])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    query = db.query(User)
    if str(current_user.role).upper() != "SUPER_ADMIN":
        query = query.filter(User.school_id == current_user.school_id)
    
    users = query.offset(skip).limit(limit).all()
    return [serialize_user(u) for u in users]


@router.get("/me", response_model=dict)
def get_my_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return serialize_user(current_user)


@router.patch("/me", response_model=dict)
def update_my_user_profile(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    allowed_fields = {"display_name", "full_name", "email", "mobile"}
    for key, value in payload.items():
        if key in allowed_fields and value is not None:
            if key == "full_name":
                current_user.display_name = str(value).strip()
            else:
                setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)


@router.get("/{user_id}", response_model=dict)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    role = str(current_user.role).upper()
    if role != "SUPER_ADMIN":
        if user.school_id != current_user.school_id and current_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return serialize_user(user)


@router.patch("/{user_id}", response_model=dict)
def update_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = str(current_user.role).upper()
    is_self = (current_user.id == user.id)
    is_admin = (role in ["SUPER_ADMIN", "PRINCIPAL"])

    if not is_self and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if is_admin and role != "SUPER_ADMIN" and user.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed_fields = {"display_name", "full_name", "email", "mobile"}
    if is_admin:
        allowed_fields.add("is_active")

    for key, value in payload.items():
        if key in allowed_fields and value is not None:
            if key == "full_name":
                user.display_name = str(value).strip()
            else:
                setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return serialize_user(user)