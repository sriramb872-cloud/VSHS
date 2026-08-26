"""
SCHOLARIS ERP - Teacher Service
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.teacher import TeacherRepository
from app.repositories.user import UserRepository
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse
from app.schemas.user import UserCreate
from app.models.role import UserRole


class TeacherService:
    def __init__(self, db: Session):
        self.repo = TeacherRepository(db)
        self.user_repo = UserRepository(db)

    def get_by_id(self, teacher_id: int) -> TeacherResponse:
        obj = self.repo.get_by_id(teacher_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
        return TeacherResponse.model_validate(obj)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[TeacherResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [TeacherResponse.model_validate(i) for i in items]

    def create_teacher(self, obj_in: TeacherCreate) -> TeacherResponse:
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
                        role=UserRole.TEACHER,
                        school_id=obj_in.school_id,
                    )
                )
                obj_in.user_id = new_user.id

        obj = self.repo.create(obj_in)
        return TeacherResponse.model_validate(obj)

    def update(self, teacher_id: int, obj_in: TeacherUpdate) -> TeacherResponse:
        obj = self.repo.get_by_id(teacher_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
        updated = self.repo.update(obj, obj_in)
        return TeacherResponse.model_validate(updated)

    def delete(self, teacher_id: int) -> None:
        obj = self.repo.get_by_id(teacher_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
        self.repo.delete(teacher_id)
