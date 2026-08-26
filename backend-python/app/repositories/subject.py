"""
SCHOLARIS ERP - Subject Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.subject import Subject
from app.schemas.subject import SubjectCreate, SubjectUpdate


class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subject_id: int) -> Optional[Subject]:
        return self.db.query(Subject).filter(Subject.id == subject_id).first()

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[Subject]:
        return self.db.query(Subject).filter(Subject.school_id == school_id).offset(skip).limit(limit).all()

    def get_by_grade(self, school_id: int, grade_id: int) -> List[Subject]:
        from app.models.grade_subject import GradeSubject
        return self.db.query(Subject).join(
            GradeSubject, GradeSubject.subject_id == Subject.id
        ).filter(
            Subject.school_id == school_id,
            GradeSubject.grade_id == grade_id
        ).all()

    def create(self, obj_in: SubjectCreate) -> Subject:
        db_obj = Subject(
            name=obj_in.name,
            code=obj_in.code,
            description=obj_in.description,
            is_elective=obj_in.is_elective,
            school_id=obj_in.school_id,
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Subject, obj_in: SubjectUpdate) -> Subject:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, subject_id: int) -> Optional[Subject]:
        obj = self.get_by_id(subject_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
