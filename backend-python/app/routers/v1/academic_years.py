# backend-python/app/routers/v1/academic_years.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import academic_year as ay_crud
from app.models.user import User
from app.schemas.academic_year import AcademicYearCreate

router = APIRouter(prefix="/academic-years", tags=["Academic Years"])


@router.get("", response_model=List[dict])
def list_academic_years(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")
    
    years = ay_crud.get_academic_years_by_school(db, school_id=school_id, skip=skip, limit=limit)
    return [
        {
            "id": y.id,
            "school_id": y.school_id,
            "name": getattr(y, "name", ""),
            "is_active": getattr(y, "is_active", False),
            "start_date": getattr(y, "start_date", None),
            "end_date": getattr(y, "end_date", None)
        }
        for y in years
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_academic_year(
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    school_id = current_user.school_id
    if not school_id and current_user.role == "SUPER_ADMIN":
        school_id = payload.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School ID is required")

    name = payload.name
    if name and ay_crud.get_academic_year_by_name(db, school_id, name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year name already exists")

    item = ay_crud.create_academic_year(db, school_id, payload.model_dump())
    return {
        "id": item.id,
        "school_id": item.school_id,
        "name": getattr(item, "name", ""),
        "is_active": getattr(item, "is_active", False)
    }


@router.get("/{academic_year_id}", response_model=dict)
def get_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    
    if str(current_user.role).upper() != "SUPER_ADMIN" and item.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return {
        "id": item.id,
        "school_id": item.school_id,
        "name": getattr(item, "name", ""),
        "is_active": getattr(item, "is_active", False)
    }


@router.patch("/{academic_year_id}", response_model=dict)
def update_academic_year(
    academic_year_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and item.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    updated = ay_crud.update_academic_year(db, item, payload)
    return {
        "id": updated.id,
        "school_id": updated.school_id,
        "name": getattr(updated, "name", ""),
        "is_active": getattr(updated, "is_active", False)
    }