# backend-python/app/crud/exam.py
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.exam import ExamModel
from app.schemas.exam import ExamCreate, ExamUpdate


class CRUDExam:
    def get(self, db: Session, exam_id: int) -> Optional[ExamModel]:
        return db.query(ExamModel).filter(ExamModel.id == exam_id).first()

    def get_multi(
        self,
        db: Session,
        *,
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
        end_date: Optional[date] = None
    ) -> Tuple[List[ExamModel], int]:
        query = db.query(ExamModel)
        if school_id is not None:
            query = query.filter(ExamModel.school_id == school_id)
        if academic_year_id is not None:
            query = query.filter(ExamModel.academic_year_id == academic_year_id)
        if exam_type is not None:
            query = query.filter(ExamModel.exam_type == exam_type)
        if grade_id is not None:
            query = query.filter(ExamModel.grade_id == grade_id)
        if section_id is not None:
            query = query.filter(ExamModel.section_id == section_id)
        if subject_id is not None:
            query = query.filter(ExamModel.subject_id == subject_id)
        if teacher_id is not None:
            query = query.filter(ExamModel.teacher_id == teacher_id)
        if start_date is not None:
            query = query.filter((ExamModel.exam_date >= start_date) | (ExamModel.start_date >= start_date))
        if end_date is not None:
            query = query.filter((ExamModel.exam_date <= end_date) | (ExamModel.end_date <= end_date))

        total = query.count()
        items = query.order_by(ExamModel.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, db: Session, *, obj_in: ExamCreate, school_id: int, teacher_id: Optional[int] = None) -> ExamModel:
        db_obj = ExamModel(
            school_id=school_id,
            academic_year_id=obj_in.academic_year_id,
            name=obj_in.name,
            exam_type=obj_in.exam_type,
            grade_id=obj_in.grade_id,
            section_id=obj_in.section_id,
            subject_id=obj_in.subject_id,
            teacher_id=teacher_id or getattr(obj_in, "teacher_id", 1),
            exam_date=obj_in.exam_date,
            start_date=obj_in.exam_date,
            end_date=obj_in.exam_date,
            start_time=obj_in.start_time,
            end_time=obj_in.end_time,
            maximum_marks=obj_in.maximum_marks,
            passing_marks=obj_in.passing_marks,
            instructions=obj_in.instructions,
            status="SCHEDULED",
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ExamModel, obj_in: ExamUpdate) -> ExamModel:
        update_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            if field == "exam_date" and value is not None:
                db_obj.start_date = value
                db_obj.end_date = value
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> ExamModel:
        obj = db.query(ExamModel).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


exam = CRUDExam()