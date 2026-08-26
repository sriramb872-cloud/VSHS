"""
SCHOLARIS ERP - Grade Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.grade import Grade
from app.schemas.grade import GradeCreate, GradeUpdate


class GradeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, grade_id: int) -> Optional[Grade]:
        return self.db.query(Grade).filter(Grade.id == grade_id).first()

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[Grade]:
        return self.db.query(Grade).filter(Grade.school_id == school_id).offset(skip).limit(limit).all()

    def create(self, obj_in: GradeCreate) -> Grade:
        db_obj = Grade(
            name=obj_in.name,
            code=obj_in.code,
            description=obj_in.description,
            school_id=obj_in.school_id
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Grade, obj_in: GradeUpdate) -> Grade:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, grade_id: int) -> Optional[Grade]:
        obj = self.get_by_id(grade_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
