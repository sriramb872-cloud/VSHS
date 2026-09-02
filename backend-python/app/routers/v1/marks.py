# app/routers/v1/marks.py
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.marks import (
    MarksSubmitPayload,
    FormativeMarksSubmitPayload,
    MarksListResponse,
    MarkResponse,
    StudentMarksViewResponse,
)
from app.services.marks import MarksService
from app.models.user import UserModel

router = APIRouter(prefix="/marks", tags=["Marks"])


@router.get("/", response_model=MarksListResponse)
def list_marks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    exam_id: Optional[int] = None,
    exam_subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    items, total = MarksService.list_marks(
        db,
        skip=skip,
        limit=limit,
        exam_id=exam_id,
        exam_subject_id=exam_subject_id,
        student_id=student_id,
        school_id=school_id,
    )
    return {"total": total, "items": items}


@router.get("/my-marks", response_model=StudentMarksViewResponse)
def get_my_marks(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return MarksService.get_student_marks_view(db, current_user=current_user)


@router.post("/submit", response_model=List[MarkResponse], status_code=status.HTTP_200_OK)
def submit_marks(
    obj_in: MarksSubmitPayload,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return MarksService.submit_marks(db, payload=obj_in, current_user=current_user)


@router.post("/submit-formative", status_code=status.HTTP_200_OK)
def submit_formative_marks(
    obj_in: FormativeMarksSubmitPayload,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return MarksService.submit_formative_marks(db, payload=obj_in, current_user=current_user)


@router.post("/", response_model=List[MarkResponse], status_code=status.HTTP_200_OK)
def save_marks(
    obj_in: MarksSubmitPayload,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return MarksService.submit_marks(db, payload=obj_in, current_user=current_user)