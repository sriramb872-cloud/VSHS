# app/routers/v1/marks.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.marks import (
    MarksEntryCreate,
    MarksListResponse,
    MarkResponse,
)
from app.services.marks import MarksService
from app.models.user import UserModel

router = APIRouter(prefix="/marks", tags=["Marks"])


@router.get("/", response_model=MarksListResponse)
def list_marks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    exam_id: Optional[int] = None,
    student_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    academic_year_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    items, total = MarksService.list_marks(
        db,
        skip=skip,
        limit=limit,
        exam_id=exam_id,
        student_id=student_id,
        grade_id=grade_id,
        section_id=section_id,
        subject_id=subject_id,
        academic_year_id=academic_year_id,
        teacher_id=teacher_id,
    )
    return {"total": total, "items": items}

@router.post("/", response_model=list[MarkResponse], status_code=status.HTTP_201_CREATED)
def save_marks(
    obj_in: MarksEntryCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return MarksService.save_marks(db, obj_in=obj_in)