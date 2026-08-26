"""
SCHOLARIS ERP - Student Enrollment Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.student_enrollment import StudentEnrollmentRepository
from app.schemas.student_enrollment import StudentEnrollmentCreate, StudentEnrollmentUpdate, StudentEnrollmentResponse


class StudentEnrollmentService:
    def __init__(self, db: Session):
        self.repo = StudentEnrollmentRepository(db)

    def get_by_id(self, enrollment_id: int) -> StudentEnrollmentResponse:
        obj = self.repo.get_by_id(enrollment_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")
        return StudentEnrollmentResponse.model_validate(obj)

    def get_student_history(self, student_id: int) -> List[StudentEnrollmentResponse]:
        items = self.repo.get_history_by_student(student_id)
        return [StudentEnrollmentResponse.model_validate(i) for i in items]

    def create(self, obj_in: StudentEnrollmentCreate) -> StudentEnrollmentResponse:
        existing = self.repo.get_by_student_and_year(obj_in.student_id, obj_in.academic_year_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is already enrolled for this academic year"
            )
        obj = self.repo.create(obj_in)
        return StudentEnrollmentResponse.model_validate(obj)

    def update(self, enrollment_id: int, obj_in: StudentEnrollmentUpdate) -> StudentEnrollmentResponse:
        obj = self.repo.get_by_id(enrollment_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")
        updated = self.repo.update(obj, obj_in)
        return StudentEnrollmentResponse.model_validate(updated)

    def delete(self, enrollment_id: int) -> None:
        obj = self.repo.get_by_id(enrollment_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")
        self.repo.delete(enrollment_id)
