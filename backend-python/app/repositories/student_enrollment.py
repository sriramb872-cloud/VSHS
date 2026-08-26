"""
SCHOLARIS ERP - Student Enrollment Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.student_enrollment import StudentEnrollment
from app.schemas.student_enrollment import StudentEnrollmentCreate, StudentEnrollmentUpdate


class StudentEnrollmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, enrollment_id: int) -> Optional[StudentEnrollment]:
        return self.db.query(StudentEnrollment).filter(StudentEnrollment.id == enrollment_id).first()

    def get_by_student_and_year(self, student_id: int, academic_year_id: int) -> Optional[StudentEnrollment]:
        return self.db.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == student_id,
            StudentEnrollment.academic_year_id == academic_year_id
        ).first()

    def get_history_by_student(self, student_id: int) -> List[StudentEnrollment]:
        return self.db.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == student_id
        ).order_by(StudentEnrollment.created_at.desc()).all()

    def get_by_section_and_year(
        self, school_id: int, academic_year_id: int, grade_id: int, section_id: int
    ) -> List[StudentEnrollment]:
        from app.models.student import Student
        from app.models.section import Section
        return self.db.query(StudentEnrollment).join(
            Student, Student.id == StudentEnrollment.student_id
        ).join(
            Section, Section.id == StudentEnrollment.section_id
        ).filter(
            Student.school_id == school_id,
            StudentEnrollment.academic_year_id == academic_year_id,
            Section.grade_id == grade_id,
            StudentEnrollment.section_id == section_id
        ).all()

    def create(self, obj_in: StudentEnrollmentCreate) -> StudentEnrollment:
        db_obj = StudentEnrollment(
            student_id=obj_in.student_id,
            academic_year_id=obj_in.academic_year_id,
            section_id=obj_in.section_id,
            roll_number=obj_in.roll_number,
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: StudentEnrollment, obj_in: StudentEnrollmentUpdate) -> StudentEnrollment:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, enrollment_id: int) -> Optional[StudentEnrollment]:
        obj = self.get_by_id(enrollment_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
