# backend-python/app/routers/v1/academic_years.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import academic_year as ay_crud
from app.models.user import User
from app.models.academic_year import AcademicYear
from app.models.exam import Exam
from app.models.timetable import Timetable
from app.models.exam_subject import ExamSubject
from app.models.marks import Marks
from app.core.audit import write_audit_log
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

    # Enforce single active academic year per school
    if payload.get("is_active") is True or payload.get("is_active") == "true":
        db.query(AcademicYear).filter(
            AcademicYear.school_id == item.school_id,
            AcademicYear.id != item.id,
        ).update({"is_active": False})
        db.flush()

    updated = ay_crud.update_academic_year(db, item, payload)
    write_audit_log(
        db, user_id=current_user.id, school_id=item.school_id,
        action="UPDATE", resource_type="AcademicYear", resource_id=item.id,
        details={k: str(v) for k, v in payload.items()}
    )
    return {
        "id": updated.id,
        "school_id": updated.school_id,
        "name": getattr(updated, "name", ""),
        "is_active": getattr(updated, "is_active", False),
        "start_date": str(getattr(updated, "start_date", "") or ""),
        "end_date": str(getattr(updated, "end_date", "") or ""),
    }


@router.delete("/{academic_year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and item.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if getattr(item, "is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the currently active academic year."
        )

    blocking = []
    if getattr(item, "enrollments", None) and len(item.enrollments) > 0:
        blocking.append("student enrollments")
    if db.query(Exam).filter(Exam.academic_year_id == academic_year_id).first():
        blocking.append("exams")
    if db.query(Timetable).filter(Timetable.academic_year_id == academic_year_id).first():
        blocking.append("timetable entries")
    if db.query(Marks).join(ExamSubject).join(Exam).filter(Exam.academic_year_id == academic_year_id).first():
        blocking.append("recorded marks")
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: this academic year has {', '.join(blocking)}. Archive it instead."
        )

    ay_name = getattr(item, "name", "")
    school_id = item.school_id
    ay_crud.delete_academic_year(db, item)
    write_audit_log(
        db, user_id=current_user.id, school_id=school_id,
        action="DELETE", resource_type="AcademicYear", resource_id=academic_year_id,
        details={"name": ay_name}
    )
    return None