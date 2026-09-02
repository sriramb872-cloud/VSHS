# backend-python/app/crud/exam.py
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.exam import ExamModel
from app.models.exam_subject import ExamSubject
from app.schemas.exam import ExamCreate, ExamUpdate


class CRUDExam:
    def get(self, db: Session, exam_id: int) -> Optional[ExamModel]:
        return (
            db.query(ExamModel)
            .options(
                joinedload(ExamModel.exam_subjects).joinedload(ExamSubject.subject),
                joinedload(ExamModel.exam_subjects).joinedload(ExamSubject.teacher),
                joinedload(ExamModel.grade),
                joinedload(ExamModel.section),
            )
            .filter(ExamModel.id == exam_id)
            .first()
        )

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 20,
        school_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        exam_type: Optional[str] = None,
        assessment_mode: Optional[str] = None,
        status: Optional[str] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[ExamModel], int]:
        query = db.query(ExamModel).options(
            joinedload(ExamModel.exam_subjects).joinedload(ExamSubject.subject),
            joinedload(ExamModel.exam_subjects).joinedload(ExamSubject.teacher),
            joinedload(ExamModel.grade),
            joinedload(ExamModel.section),
        )

        if school_id is not None:
            query = query.filter(ExamModel.school_id == school_id)
        if academic_year_id is not None:
            query = query.filter(ExamModel.academic_year_id == academic_year_id)
        if exam_type is not None:
            query = query.filter(ExamModel.exam_type == exam_type)
        if assessment_mode is not None:
            query = query.filter(ExamModel.assessment_mode == assessment_mode)
        if status is not None:
            query = query.filter(ExamModel.status == status)
        if grade_id is not None:
            query = query.filter(ExamModel.grade_id == grade_id)
        if section_id is not None:
            query = query.filter(ExamModel.section_id == section_id)
        if teacher_id is not None:
            query = query.join(ExamModel.exam_subjects).filter(ExamSubject.teacher_id == teacher_id)
        if start_date is not None:
            query = query.filter(ExamModel.start_date >= start_date)
        if end_date is not None:
            query = query.filter(ExamModel.end_date <= end_date)

        query = query.distinct()
        total = query.count()
        items = query.order_by(ExamModel.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(
        self,
        db: Session,
        *,
        obj_in: ExamCreate,
        school_id: int,
        created_by_id: Optional[int] = None,
    ) -> ExamModel:
        db_obj = ExamModel(
            school_id=school_id,
            academic_year_id=obj_in.academic_year_id,
            name=obj_in.name,
            exam_type=obj_in.exam_type,
            assessment_mode=obj_in.assessment_mode or "FORMATIVE",
            grade_id=obj_in.grade_id,
            section_id=obj_in.section_id,
            start_date=obj_in.start_date,
            end_date=obj_in.end_date,
            status="SCHEDULED",
            created_by_id=created_by_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ExamModel, obj_in: ExamUpdate) -> ExamModel:
        update_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ExamModel]:
        obj = db.query(ExamModel).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


exam = CRUDExam()