"""
SCHOLARIS ERP - School Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolUpdate


class SchoolRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, school_id: int) -> Optional[School]:
        return self.db.query(School).filter(School.id == school_id).first()

    def get_by_code(self, code: str) -> Optional[School]:
        return self.db.query(School).filter(School.code == code).first()

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[School]:
        return self.db.query(School).offset(skip).limit(limit).all()

    def create(self, obj_in: SchoolCreate) -> School:
        db_obj = School(
            name=obj_in.name,
            code=obj_in.code,
            address=obj_in.address,
            phone=obj_in.phone,
            email=obj_in.email,
            website=obj_in.website,
            logo_url=obj_in.logo_url,
            is_active=obj_in.is_active
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: School, obj_in: SchoolUpdate) -> School:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, school_id: int) -> Optional[School]:
        obj = self.get_by_id(school_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
