# app/routers/v1/timetable.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.timetable import (
    TimetableResponse,
    TimetableListResponse,
    TimetableCreate,
    TimetableUpdate,
    TimetableCopy,
)
from app.services.timetable import TimetableService
from app.models.user import UserModel

router = APIRouter(prefix="/timetables", tags=["Timetables"])


@router.get("", response_model=TimetableListResponse)
@router.get("/", response_model=TimetableListResponse)
def list_timetables(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    academic_year_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    if str(current_user.role).upper() == "TEACHER":
        from app.models.teacher import Teacher
        teacher = getattr(current_user, "teacher_profile", None) or (
            db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        )
        if teacher:
            teacher_id = teacher.id

    items, total = TimetableService.list_timetables(
        db,
        skip=skip,
        limit=limit,
        academic_year_id=academic_year_id,
        grade_id=grade_id,
        section_id=section_id,
        teacher_id=teacher_id,
        school_id=school_id,
    )
    return {"total": total, "items": items}


@router.get("/{timetable_id}", response_model=TimetableResponse)
def get_timetable(
    timetable_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    return TimetableService.get_timetable(db, timetable_id=timetable_id, school_id=school_id)


@router.post("", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED)
def create_timetable(
    obj_in: TimetableCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")
    return TimetableService.create_timetable(db, obj_in=obj_in, school_id=school_id)


@router.put("/{timetable_id}", response_model=TimetableResponse)
@router.patch("/{timetable_id}", response_model=TimetableResponse)
def update_timetable(
    timetable_id: int,
    obj_in: TimetableUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    return TimetableService.update_timetable(db, timetable_id=timetable_id, obj_in=obj_in, school_id=school_id)


@router.delete("/{timetable_id}", response_model=TimetableResponse)
def delete_timetable(
    timetable_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    return TimetableService.delete_timetable(db, timetable_id=timetable_id, school_id=school_id)


@router.post("/{timetable_id}/copy", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED)
def copy_timetable(
    timetable_id: int,
    copy_in: TimetableCopy,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    return TimetableService.copy_timetable(db, timetable_id=timetable_id, copy_in=copy_in, school_id=school_id)