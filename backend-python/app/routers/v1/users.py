# backend-python/app/routers/v1/users.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user, require_roles
from app.models.user import User
from app.core.security import get_password_hash
from app.core.audit import write_audit_log
from app.core.audit import write_audit_log

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
    role: Optional[str] = Query(None, description="Filter by role: SUPER_ADMIN, PRINCIPAL, TEACHER, STUDENT"),
    search: Optional[str] = Query(None, description="Search by name, mobile, or email"),
    is_active: Optional[str] = Query(None, description="Filter by active status"),
    school_id: Optional[int] = Query(None, description="Filter by school (SUPER_ADMIN only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    query = db.query(User)
    if str(current_user.role).upper() != "SUPER_ADMIN":
        query = query.filter(User.school_id == current_user.school_id)
    elif school_id is not None:
        query = query.filter(User.school_id == school_id)

    if role:
        query = query.filter(User.role == role.upper())
    if is_active:
        query = query.filter(User.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            (User.display_name.ilike(like)) | (User.mobile.ilike(like)) | (User.email.ilike(like))
        )

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


@router.post("/{user_id}/reset-password", response_model=dict)
def reset_user_password(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if str(current_user.role).upper() != "SUPER_ADMIN" and user.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    password = payload.get("password")
    if not isinstance(password, str) or len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long")
    user.password_hash = get_password_hash(password)
    user.must_change_password = True
    db.commit()
    write_audit_log(db, user_id=current_user.id, school_id=user.school_id, action="RESET_PASSWORD",
                    resource_type="User", resource_id=user.id, details={})
    return {"message": "Password reset successfully"}


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

    if is_self and role == "SUPER_ADMIN" and "is_active" in payload:
        new_active = payload["is_active"]
        if new_active is False or str(new_active).upper() not in ["ACTIVE", "TRUE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Super Admin cannot deactivate their own account"
            )

    for key, value in payload.items():
        if key in allowed_fields and value is not None:
            if key == "full_name":
                user.display_name = str(value).strip()
            elif key == "is_active":
                user.is_active = "ACTIVE" if value is True or str(value).upper() == "ACTIVE" else "INACTIVE"
            else:
                setattr(user, key, value)

    db.commit()
    db.refresh(user)

    write_audit_log(
        db, user_id=current_user.id, school_id=user.school_id,
        action="UPDATE", resource_type="User", resource_id=user.id,
        details={k: str(v) for k, v in payload.items() if k in allowed_fields}
    )

    return serialize_user(user)
