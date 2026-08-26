"""
SCHOLARIS ERP - Student Service
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.student import StudentRepository
from app.repositories.user import UserRepository
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.schemas.user import UserCreate
from app.models.role import UserRole


class StudentService:
    def __init__(self, db: Session):
        self.repo = StudentRepository(db)
        self.user_repo = UserRepository(db)

    def get_by_id(self, student_id: int) -> StudentResponse:
        obj = self.repo.get_by_id(student_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        return StudentResponse.model_validate(obj)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[StudentResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [StudentResponse.model_validate(i) for i in items]

    def create_student(self, obj_in: StudentCreate) -> StudentResponse:
        existing = self.repo.get_by_admission_number(obj_in.school_id, obj_in.admission_number)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admission number already exists for this school")

        # Create linked user account if email provided and user_id not already specified
        if not obj_in.user_id and obj_in.email:
            user_existing = self.user_repo.get_by_email(obj_in.email)
            if user_existing:
                obj_in.user_id = user_existing.id
            else:
                new_user = self.user_repo.create(
                    UserCreate(
                        email=obj_in.email,
                        full_name=f"{obj_in.first_name} {obj_in.last_name}",
                        role=UserRole.STUDENT,
                        school_id=obj_in.school_id,
                    )
                )
                obj_in.user_id = new_user.id

        obj = self.repo.create(obj_in)
        return StudentResponse.model_validate(obj)

    def update(self, student_id: int, obj_in: StudentUpdate) -> StudentResponse:
        obj = self.repo.get_by_id(student_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        updated = self.repo.update(obj, obj_in)
        return StudentResponse.model_validate(updated)

    def delete(self, student_id: int) -> None:
        obj = self.repo.get_by_id(student_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        self.repo.delete(student_id)
