# app/services/marks.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.exam_result import ExamResult
from app.schemas.marks import MarksEntryCreate


class MarksService:
    @staticmethod
    def list_marks(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        exam_id: Optional[int] = None,
        student_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> Tuple[List[ExamResult], int]:
        from app.models.student import Student
        if school_id is not None:
            query = db.query(ExamResult).join(Student, ExamResult.student_id == Student.id).filter(
                Student.school_id == school_id
            )
        else:
            query = db.query(ExamResult)
        if exam_id is not None:
            query = query.filter(ExamResult.exam_id == exam_id)
        if student_id is not None:
            query = query.filter(ExamResult.student_id == student_id)
        if subject_id is not None:
            query = query.filter(ExamResult.subject_id == subject_id)

        total = query.count()
        items = query.order_by(ExamResult.id.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def save_marks(db: Session, obj_in: MarksEntryCreate) -> List[ExamResult]:
        saved_items = []
        for mark_item in obj_in.marks:
            existing = (
                db.query(ExamResult)
                .filter(
                    ExamResult.exam_id == obj_in.exam_id,
                    ExamResult.student_id == mark_item.student_id,
                )
                .first()
            )
            if existing:
                existing.written_test = mark_item.marks_obtained
                db.add(existing)
                saved_items.append(existing)
            else:
                new_item = ExamResult(
                    exam_id=obj_in.exam_id,
                    student_id=mark_item.student_id,
                    subject_id=getattr(obj_in, "subject_id", 1),
                    written_test=mark_item.marks_obtained,
                )
                db.add(new_item)
                saved_items.append(new_item)
        db.commit()
        for item in saved_items:
            db.refresh(item)
        return saved_items
