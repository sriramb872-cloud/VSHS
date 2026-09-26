# backend-python/app/routers/v1/schools.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import school as school_crud
from app.models.user import User
from app.core.audit import write_audit_log

router = APIRouter(prefix="/schools", tags=["Schools"])


@router.get("", response_model=List[dict])
def list_schools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    role = str(current_user.role).upper()
    if role == "SUPER_ADMIN":
        schools = school_crud.get_schools(db, skip=skip, limit=limit)
    else:
        if not current_user.school_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School context missing")
        school = school_crud.get_school(db, current_user.school_id)
        schools = [school] if school else []

    return [
        {
            "id": s.id,
            "name": getattr(s, "name", ""),
            "code": getattr(s, "code", ""),
            "is_active": getattr(s, "is_active", True),
            "created_at": getattr(s, "created_at", None),
            "updated_at": getattr(s, "updated_at", None)
        }
        for s in schools if s
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_school(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"]))
):
    code = payload.get("code")
    if code and school_crud.get_school_by_code(db, code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School code already exists")
    
    school = school_crud.create_school(db, payload)
    write_audit_log(
        db, user_id=current_user.id, school_id=school.id,
        action="CREATE", resource_type="School", resource_id=school.id,
        details={"name": getattr(school, "name", ""), "code": getattr(school, "code", "")},
    )
    return {
        "id": school.id,
        "name": getattr(school, "name", ""),
        "code": getattr(school, "code", ""),
        "is_active": getattr(school, "is_active", True)
    }


@router.get("/{school_id}", response_model=dict)
def get_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    role = str(current_user.role).upper()
    if role != "SUPER_ADMIN" and current_user.school_id != school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    school = school_crud.get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    return {
        "id": school.id,
        "name": getattr(school, "name", ""),
        "code": getattr(school, "code", ""),
        "is_active": getattr(school, "is_active", True),
        "created_at": getattr(school, "created_at", None),
        "updated_at": getattr(school, "updated_at", None)
    }


@router.patch("/{school_id}", response_model=dict)
def update_school(
    school_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"]))
):
    school = school_crud.get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    updated = school_crud.update_school(db, school, payload)
    write_audit_log(
        db, user_id=current_user.id, school_id=updated.id,
        action="UPDATE", resource_type="School", resource_id=updated.id, details=payload,
    )
    return {
        "id": updated.id,
        "name": getattr(updated, "name", ""),
        "code": getattr(updated, "code", ""),
        "is_active": getattr(updated, "is_active", True)
    }


@router.post("/{school_id}/lifecycle", response_model=dict)
def update_school_lifecycle(
    school_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    school = school_crud.get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
    action = str(payload.get("action", "")).upper()
    if action not in {"DEACTIVATE", "REACTIVATE"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be DEACTIVATE or REACTIVATE")
    updated = school_crud.update_school(db, school, {"is_active": action == "REACTIVATE"})
    write_audit_log(db, user_id=current_user.id, school_id=updated.id, action=action,
                    resource_type="School", resource_id=updated.id, details={})
    return {"id": updated.id, "name": updated.name, "code": updated.code, "is_active": updated.is_active}


@router.patch("/{school_id}/status", response_model=dict)
def update_school_status(
    school_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"]))
):
    """Activate or deactivate a school (SUPER_ADMIN only)."""
    school = school_crud.get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    new_status = payload.get("is_active")
    if new_status is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="is_active is required")

    old_status = getattr(school, "is_active", None)
    school.is_active = bool(new_status)
    db.commit()
    db.refresh(school)

    action = "ACTIVATE" if new_status else "DEACTIVATE"
    write_audit_log(
        db, user_id=current_user.id, school_id=school.id,
        action=action, resource_type="School", resource_id=school.id,
        details={"is_active": new_status, "previous": old_status},
    )
    return {
        "id": school.id,
        "name": getattr(school, "name", ""),
        "code": getattr(school, "code", ""),
        "is_active": getattr(school, "is_active", True)
    }
