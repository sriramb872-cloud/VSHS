# app/services/exam.py
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.exam import exam as crud_exam
from app.schemas.exam import ExamCreate, ExamUpdate
from app.models.exam import Exam

class ExamService:
    @staticmethod
    def get_exam(db: Session, exam_id: int, school_id: Optional[int] = None) -> Optional[Exam]:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return None
        if school_id is not None and db_obj.school_id != school_id:
            return None
        return db_obj

    @staticmethod
    def list_exams(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        school_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        exam_type: Optional[str] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[Exam], int]:
        return crud_exam.get_multi(
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

    @staticmethod
    def create_exam(db: Session, obj_in: ExamCreate, school_id: int, teacher_id: Optional[int] = None) -> Exam:
        return crud_exam.create(db, obj_in=obj_in, school_id=school_id, teacher_id=teacher_id)

    @staticmethod
    def update_exam(
        db: Session, exam_id: int, obj_in: ExamUpdate, school_id: Optional[int] = None
    ) -> Optional[Exam]:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return None
        if school_id is not None and db_obj.school_id != school_id:
            return None
        return crud_exam.update(db, db_obj=db_obj, obj_in=obj_in)

    @staticmethod
    def delete_exam(db: Session, exam_id: int, school_id: Optional[int] = None) -> bool:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return False
        if school_id is not None and db_obj.school_id != school_id:
            return False
        crud_exam.remove(db, id=exam_id)
        return True