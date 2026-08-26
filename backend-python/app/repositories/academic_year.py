"""
SCHOLARIS ERP - Academic Year Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.academic_year import AcademicYear
from app.schemas.academic_year import AcademicYearCreate, AcademicYearUpdate


class AcademicYearRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, academic_year_id: int) -> Optional[AcademicYear]:
        return self.db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()

    def get_active_for_school(self, school_id: int) -> Optional[AcademicYear]:
        return self.db.query(AcademicYear).filter(
            AcademicYear.school_id == school_id,
            AcademicYear.is_active.is_(True)
        ).first()

    def get_all_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[AcademicYear]:
        return self.db.query(AcademicYear).filter(
            AcademicYear.school_id == school_id
        ).offset(skip).limit(limit).all()

    def create(self, obj_in: AcademicYearCreate) -> AcademicYear:
        db_obj = AcademicYear(
            name=obj_in.name,
            start_date=obj_in.start_date,
            end_date=obj_in.end_date,
            is_active=obj_in.is_active,
            school_id=obj_in.school_id
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: AcademicYear, obj_in: AcademicYearUpdate) -> AcademicYear:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, academic_year_id: int) -> Optional[AcademicYear]:
        obj = self.get_by_id(academic_year_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
