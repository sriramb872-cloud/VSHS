"""
SCHOLARIS ERP - Student Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.schemas.student import StudentCreate, StudentUpdate


class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, student_id: int) -> Optional[Student]:
        return self.db.query(Student).filter(Student.id == student_id).first()

    def get_by_user_id(self, user_id: int) -> Optional[Student]:
        return self.db.query(Student).filter(Student.user_id == user_id).first()

    def get_by_admission_number(self, school_id: int, admission_number: str) -> Optional[Student]:
        return self.db.query(Student).filter(
            Student.school_id == school_id,
            Student.admission_number == admission_number
        ).first()

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[Student]:
        return self.db.query(Student).filter(
            Student.school_id == school_id
        ).offset(skip).limit(limit).all()

    def get_by_section(self, school_id: int, grade_id: int, section_id: int) -> List[Student]:
        return self.db.query(Student).join(
            StudentEnrollment, StudentEnrollment.student_id == Student.id
        ).filter(
            Student.school_id == school_id,
            StudentEnrollment.section_id == section_id,
        ).all()

    def create(self, obj_in: StudentCreate) -> Student:
        db_obj = Student(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            admission_number=obj_in.admission_number,
            date_of_birth=obj_in.date_of_birth,
            gender=obj_in.gender,
            address=obj_in.address,
            blood_group=obj_in.blood_group,
            emergency_contact=obj_in.emergency_contact,
            user_id=obj_in.user_id,
            school_id=obj_in.school_id,
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Student, obj_in: StudentUpdate) -> Student:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, student_id: int) -> Optional[Student]:
        obj = self.get_by_id(student_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
