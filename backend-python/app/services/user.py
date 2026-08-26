"""
SCHOLARIS ERP - User Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def get_by_id(self, user_id: int) -> UserResponse:
        obj = self.repo.get_by_id(user_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(obj)

    def get_by_email(self, email: str) -> UserResponse:
        obj = self.repo.get_by_email(email)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(obj)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [UserResponse.model_validate(i) for i in items]

    def create(self, obj_in: UserCreate) -> UserResponse:
        existing = self.repo.get_by_email(obj_in.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        obj = self.repo.create(obj_in)
        return UserResponse.model_validate(obj)

    def update(self, user_id: int, obj_in: UserUpdate) -> UserResponse:
        obj = self.repo.get_by_id(user_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if obj_in.email and obj_in.email != obj.email:
            existing = self.repo.get_by_email(obj_in.email)
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        updated = self.repo.update(obj, obj_in)
        return UserResponse.model_validate(updated)

    def delete(self, user_id: int) -> None:
        obj = self.repo.get_by_id(user_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        self.repo.delete(user_id)
