# backend-python/app/routers/v1/grades.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import grade as grade_crud
from app.models.user import User

router = APIRouter(prefix="/grades", tags=["Grades"])


@router.get("", response_model=List[dict])
def list_grades(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    grades = grade_crud.get_grades_by_school(db, school_id=school_id, skip=skip, limit=limit)
    return [
        {
            "id": g.id,
            "school_id": g.school_id,
            "name": getattr(g, "name", ""),
            "display_order": getattr(g, "display_order", 0)
        }
        for g in grades
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_grade(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    name = payload.get("name")
    if name and grade_crud.get_grade_by_name(db, school_id, name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade name already exists")

    grade = grade_crud.create_grade(db, school_id, payload)
    return {
        "id": grade.id,
        "school_id": grade.school_id,
        "name": getattr(grade, "name", "")
    }


@router.get("/{grade_id}", response_model=dict)
def get_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    grade = grade_crud.get_grade(db, grade_id)
    if not grade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and grade.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return {
        "id": grade.id,
        "school_id": grade.school_id,
        "name": getattr(grade, "name", "")
    }


@router.patch("/{grade_id}", response_model=dict)
def update_grade(
    grade_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    grade = grade_crud.get_grade(db, grade_id)
    if not grade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and grade.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    updated = grade_crud.update_grade(db, grade, payload)
    return {
        "id": updated.id,
        "school_id": updated.school_id,
        "name": getattr(updated, "name", "")
    }