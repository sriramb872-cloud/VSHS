# app/routers/v1/exam.py
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.exam import (
    ExamCreate,
    ExamListResponse,
    ExamResponse,
    ExamUpdate,
)
from app.services.exam import ExamService
from app.models.user import UserModel

router = APIRouter(prefix="/exams", tags=["Exams"])


@router.get("/", response_model=ExamListResponse)
def list_exams(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    academic_year_id: Optional[int] = None,
    exam_type: Optional[str] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    items, total = ExamService.list_exams(
        db,
        skip=skip,
        limit=limit,
        school_id=school_id,
        academic_year_id=academic_year_id,
        exam_type=exam_type,
        grade_id=grade_id,
        section_id=section_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {"total": total, "items": items}

@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam_by_id(
    exam_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    exam = ExamService.get_exam(db, exam_id=exam_id, school_id=school_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam schedule not found",
        )
    return exam

@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    obj_in: ExamCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School context not found",
        )
    return ExamService.create_exam(db, obj_in=obj_in, school_id=school_id, teacher_id=current_user.id)

@router.patch("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    obj_in: ExamUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    exam = ExamService.update_exam(db, exam_id=exam_id, obj_in=obj_in, school_id=school_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found or unauthorized to edit",
        )
    return exam

@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    success = ExamService.delete_exam(db, exam_id=exam_id, school_id=school_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found or unauthorized to delete",
        )
    return None