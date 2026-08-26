# app/routers/v1/report_card.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.report_card import (
    ReportCardResponse,
    ReportCardListResponse,
    ReportCardRemarksUpdate,
)
from app.services.report_card import ReportCardService
from app.models.user import UserModel

router = APIRouter(prefix="/report-cards", tags=["Report Cards"])


@router.get("/", response_model=ReportCardListResponse)
def list_report_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    academic_year_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    items, total = ReportCardService.list_report_cards(
        db,
        skip=skip,
        limit=limit,
        academic_year_id=academic_year_id,
        grade_id=grade_id,
        section_id=section_id,
        student_id=student_id,
    )
    return {"total": total, "items": items}

@router.get("/{student_id}", response_model=ReportCardResponse)
def get_report_card(
    student_id: int,
    academic_year_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return ReportCardService.get_report_card(db, student_id=student_id, academic_year_id=academic_year_id)

@router.patch("/{student_id}/remarks", response_model=ReportCardResponse)
def update_report_card_remarks(
    student_id: int,
    academic_year_id: int,
    obj_in: ReportCardRemarksUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return ReportCardService.update_remarks(
        db, student_id=student_id, academic_year_id=academic_year_id, teacher_remarks=obj_in.teacher_remarks
    )