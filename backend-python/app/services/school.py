"""
SCHOLARIS ERP - School Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.school import SchoolRepository
from app.schemas.school import SchoolCreate, SchoolUpdate, SchoolResponse


class SchoolService:
    def __init__(self, db: Session):
        self.repo = SchoolRepository(db)

    def get_by_id(self, school_id: int) -> SchoolResponse:
        obj = self.repo.get_by_id(school_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
        return SchoolResponse.model_validate(obj)

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[SchoolResponse]:
        items = self.repo.get_multi(skip, limit)
        return [SchoolResponse.model_validate(i) for i in items]

    def create(self, obj_in: SchoolCreate) -> SchoolResponse:
        existing = self.repo.get_by_code(obj_in.code)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School code already exists")
        obj = self.repo.create(obj_in)
        return SchoolResponse.model_validate(obj)

    def update(self, school_id: int, obj_in: SchoolUpdate) -> SchoolResponse:
        obj = self.repo.get_by_id(school_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
        if obj_in.code and obj_in.code != obj.code:
            existing = self.repo.get_by_code(obj_in.code)
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School code already in use")
        updated = self.repo.update(obj, obj_in)
        return SchoolResponse.model_validate(updated)

    def activate(self, school_id: int) -> SchoolResponse:
        return self.update(school_id, SchoolUpdate(is_active=True))

    def deactivate(self, school_id: int) -> SchoolResponse:
        return self.update(school_id, SchoolUpdate(is_active=False))

    def delete(self, school_id: int) -> None:
        obj = self.repo.get_by_id(school_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
        self.repo.delete(school_id)
