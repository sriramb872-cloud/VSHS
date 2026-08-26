"""
SCHOLARIS ERP - Teacher Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.teacher import Teacher
from app.schemas.teacher import TeacherCreate, TeacherUpdate


class TeacherRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, teacher_id: int) -> Optional[Teacher]:
        return self.db.query(Teacher).filter(Teacher.id == teacher_id).first()

    def get_by_user_id(self, user_id: int) -> Optional[Teacher]:
        return self.db.query(Teacher).filter(Teacher.user_id == user_id).first()

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[Teacher]:
        return self.db.query(Teacher).filter(Teacher.school_id == school_id).offset(skip).limit(limit).all()

    def create(self, obj_in: TeacherCreate) -> Teacher:
        db_obj = Teacher(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            employee_id=obj_in.employee_id,
            qualification=obj_in.qualification,
            user_id=obj_in.user_id,
            school_id=obj_in.school_id
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Teacher, obj_in: TeacherUpdate) -> Teacher:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, teacher_id: int) -> Optional[Teacher]:
        obj = self.get_by_id(teacher_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
