# backend-python/app/routers/v1/principals.py
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User
from app.models.principal import Principal
from app.services.id_generator import generate_principal_id

router = APIRouter(prefix="/principals", tags=["Principals"])


def _get_or_create_principal_profile(db: Session, user: User) -> Principal:
    prof = db.query(Principal).filter(Principal.user_id == user.id).first()
    if not prof and user.school_id:
        emp_id = generate_principal_id(db, user.school_id)
        join_date = user.created_at.date() if user.created_at else date.today()
        prof = Principal(
            user_id=user.id,
            school_id=user.school_id,
            employee_id=emp_id,
            joining_date=join_date,
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
    return prof


def serialize_principal(p: User, db: Optional[Session] = None) -> dict:
    school_name = None
    school_code = None
    if getattr(p, "school", None):
        school_name = getattr(p.school, "name", None) or getattr(p.school, "school_name", None)
        school_code = getattr(p.school, "code", None) or getattr(p.school, "school_code", None)

    prof = getattr(p, "principal_profile", None)
    if not prof and db:
        prof = db.query(Principal).filter(Principal.user_id == p.id).first()

    emp_id = prof.employee_id if prof and prof.employee_id else f"PRN{date.today().year}{p.id:03d}"
    joining_date = prof.joining_date if prof and prof.joining_date else (p.created_at.date() if p.created_at else date.today())

    is_active = True
    if hasattr(p, "is_active"):
        is_active = (p.is_active == "ACTIVE" or p.is_active is True)

    return {
        "id": p.id,
        "user_id": p.id,
        "school_id": p.school_id,
        "school_name": school_name,
        "school_code": school_code,
        "employee_id": emp_id,
        "joining_date": joining_date,
        "mobile": p.mobile,
        "email": p.email,
        "profile_photo": getattr(p, "profile_photo", None),
        "display_name": p.display_name,
        "full_name": p.display_name,
        "role": p.role,
        "status": "ACTIVE" if is_active else "INACTIVE",
        "is_active": is_active,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.get("", response_model=List[dict])
def list_principals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"]))
):
    principals = db.query(User).filter(User.role == "PRINCIPAL").offset(skip).limit(limit).all()
    return [serialize_principal(p, db=db) for p in principals]


@router.get("/me", response_model=dict)
def get_my_principal_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "PRINCIPAL" and str(current_user.role).upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return serialize_principal(current_user, db=db)


@router.patch("/me", response_model=dict)
def update_my_principal_profile(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "PRINCIPAL" and str(current_user.role).upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user_fields = {"display_name", "full_name", "email", "mobile", "profile_photo"}
    for k, v in payload.items():
        if k in user_fields and v is not None:
            if k == "full_name":
                current_user.display_name = str(v).strip()
            else:
                setattr(current_user, k, v)

    prof = _get_or_create_principal_profile(db, current_user)
    if prof:
        if "joining_date" in payload and payload["joining_date"]:
            jd = payload["joining_date"]
            if isinstance(jd, str) and jd.strip():
                try:
                    prof.joining_date = date.fromisoformat(jd[:10])
                except Exception:
                    pass
            elif isinstance(jd, date):
                prof.joining_date = jd

    db.commit()
    db.refresh(current_user)
    return serialize_principal(current_user, db=db)


@router.get("/{principal_id}", response_model=dict)
def get_principal(
    principal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    p = db.query(User).filter(User.id == principal_id, User.role == "PRINCIPAL").first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Principal not found")

    role = str(current_user.role).upper()
    if role != "SUPER_ADMIN" and current_user.school_id != p.school_id and current_user.id != p.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return serialize_principal(p, db=db)


@router.patch("/{principal_id}", response_model=dict)
def update_principal(
    principal_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    p = db.query(User).filter(User.id == principal_id, User.role == "PRINCIPAL").first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Principal not found")

    role = str(current_user.role).upper()
    is_self = (current_user.id == p.id)
    is_super_admin = (role == "SUPER_ADMIN")

    if not is_self and not is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user_fields = {"display_name", "full_name", "email", "mobile", "profile_photo"}
    if is_super_admin:
        user_fields.update({"is_active", "school_id", "status"})

    for k, v in payload.items():
        if k in user_fields and v is not None:
            if k == "full_name":
                p.display_name = str(v).strip()
            elif k == "status":
                p.is_active = str(v).strip()
            else:
                setattr(p, k, v)

    prof = _get_or_create_principal_profile(db, p)
    if prof:
        if is_super_admin and "employee_id" in payload and payload["employee_id"]:
            prof.employee_id = str(payload["employee_id"]).strip()
        if "joining_date" in payload and payload["joining_date"]:
            jd = payload["joining_date"]
            if isinstance(jd, str) and jd.strip():
                try:
                    prof.joining_date = date.fromisoformat(jd[:10])
                except Exception:
                    pass
            elif isinstance(jd, date):
                prof.joining_date = jd

    db.commit()
    db.refresh(p)
    return serialize_principal(p, db=db)