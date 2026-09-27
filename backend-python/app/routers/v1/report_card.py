# app/routers/v1/report_card.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.report_card import (
    ReportCardResponse,
    ReportCardListResponse,
    ReportCardRemarksUpdate,
)
from app.services.report_card import ReportCardService
from app.models.user import UserModel
from app.models.student import Student
from app.core.audit import write_audit_log

router = APIRouter(prefix="/report-cards", tags=["Report Cards"])


def _assert_section_in_school(db: Session, current_user: UserModel, section_id: int) -> None:
    """Reject a section that does not belong to the caller's school.

    SUPER_ADMIN is platform-wide and may target any school. Everyone else is
    scoped to their own ``school_id``.
    """
    from app.models.section import Section

    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    if str(current_user.role).upper() == "SUPER_ADMIN":
        return
    if not current_user.school_id or section.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Section does not belong to your school",
        )


@router.post("/generate", response_model=ReportCardListResponse)
def generate_report_cards(
    academic_year_id: int,
    section_id: int,
    exam_id: Optional[int] = None,
    term_name: str = Query("Term 1"),
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    """
    Compute and store report cards for every student in a section, based on
    PUBLISHED exams only. Safe to re-run for the same section/year/term —
    existing rows are updated rather than duplicated.
    """
    # The section id arrives as a query parameter, so it must be checked
    # against the caller's school. Without this a principal of one school could
    # regenerate (and thereby overwrite, including clearing `exam_id`) another
    # school's report cards.
    _assert_section_in_school(db, current_user, section_id)

    items = ReportCardService.generate_report_cards(
        db, academic_year_id=academic_year_id, section_id=section_id, term_name=term_name, exam_id=exam_id
    )
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="GENERATE", resource_type="ReportCard", resource_id=section_id,
        details={"academic_year_id": academic_year_id, "section_id": section_id, "term_name": term_name, "count": len(items)},
    )
    return {"total": len(items), "items": items}


@router.get("/", response_model=ReportCardListResponse)
def list_report_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    academic_year_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    student_id: Optional[int] = None,
    exam_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    role = str(current_user.role).upper()
    school_id = current_user.school_id if role != "SUPER_ADMIN" else None

    if role == "STUDENT":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student:
            return {"total": 0, "items": []}
        student_id = student.id

    items, total = ReportCardService.list_report_cards(
        db,
        skip=skip,
        limit=limit,
        academic_year_id=academic_year_id,
        grade_id=grade_id,
        section_id=section_id,
        student_id=student_id,
        exam_id=exam_id,
        school_id=school_id,
    )
    return {"total": total, "items": items}

@router.get("/{student_id}", response_model=ReportCardResponse)
def get_report_card(
    student_id: int,
    academic_year_id: int,
    exam_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    role = str(current_user.role).upper()
    school_id = current_user.school_id if role != "SUPER_ADMIN" else None

    if role == "STUDENT":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student or student.id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        student_id = student.id

    return ReportCardService.get_report_card(
        db, student_id=student_id, academic_year_id=academic_year_id, exam_id=exam_id, school_id=school_id
    )

@router.patch("/{student_id}/remarks", response_model=ReportCardResponse)
def update_report_card_remarks(
    student_id: int,
    academic_year_id: int,
    obj_in: ReportCardRemarksUpdate,
    exam_id: Optional[int] = Query(
        None,
        description=(
            "Scope the update to one examination. Without it the service "
            "matches the student's first card for the year, which is the "
            "wrong card as soon as a year has more than one exam."
        ),
    ),
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    role = str(current_user.role).upper()

    if role != "SUPER_ADMIN":
        target_student = db.query(Student).filter(Student.id == student_id).first()
        if not target_student or target_student.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: student does not belong to your school",
            )

    return ReportCardService.update_remarks(
        db,
        student_id=student_id,
        academic_year_id=academic_year_id,
        teacher_remarks=obj_in.teacher_remarks,
        exam_id=exam_id,
    )
