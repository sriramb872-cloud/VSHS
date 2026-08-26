# app/crud/report_card.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.report_card import ReportCard

class CRUDReportCard:
    def get_by_student_and_year(
        self, db: Session, *, student_id: int, academic_year_id: int
    ) -> Optional[ReportCard]:
        return db.query(ReportCard).filter(
            ReportCard.student_id == student_id,
            ReportCard.academic_year_id == academic_year_id
        ).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        student_id: Optional[int] = None,
    ) -> Tuple[List[ReportCard], int]:
        query = db.query(ReportCard)

        if academic_year_id is not None:
            query = query.filter(ReportCard.academic_year_id == academic_year_id)
        if student_id is not None:
            query = query.filter(ReportCard.student_id == student_id)
        if grade_id is not None or section_id is not None:
            from app.models.student_enrollment import StudentEnrollment
            query = query.join(
                StudentEnrollment,
                (ReportCard.student_id == StudentEnrollment.student_id) &
                (ReportCard.academic_year_id == StudentEnrollment.academic_year_id)
            )
            if grade_id is not None:
                query = query.filter(StudentEnrollment.grade_id == grade_id)
            if section_id is not None:
                query = query.filter(StudentEnrollment.section_id == section_id)

        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def update_remarks(
        self, db: Session, *, db_obj: ReportCard, teacher_remarks: str
    ) -> ReportCard:
        db_obj.remarks = teacher_remarks
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


report_card = CRUDReportCard()
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
