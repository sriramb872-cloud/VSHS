"""
SCHOLARIS ERP - Section Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.section import Section
from app.schemas.section import SectionCreate, SectionUpdate


class SectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, section_id: int) -> Optional[Section]:
        return self.db.query(Section).filter(Section.id == section_id).first()

    def get_by_grade(self, grade_id: int) -> List[Section]:
        return self.db.query(Section).filter(Section.grade_id == grade_id).all()

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[Section]:
        return self.db.query(Section).filter(Section.school_id == school_id).offset(skip).limit(limit).all()

    def create(self, obj_in: SectionCreate) -> Section:
        db_obj = Section(
            name=obj_in.name,
            grade_id=obj_in.grade_id,
            school_id=obj_in.school_id
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Section, obj_in: SectionUpdate) -> Section:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, section_id: int) -> Optional[Section]:
        obj = self.get_by_id(section_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
