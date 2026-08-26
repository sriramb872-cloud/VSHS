"""
SCHOLARIS ERP - Subject Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.subject import SubjectRepository
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse


class SubjectService:
    def __init__(self, db: Session):
        self.repo = SubjectRepository(db)

    def get_by_id(self, subject_id: int) -> SubjectResponse:
        obj = self.repo.get_by_id(subject_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        return SubjectResponse.model_validate(obj)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[SubjectResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [SubjectResponse.model_validate(i) for i in items]

    def create(self, obj_in: SubjectCreate) -> SubjectResponse:
        obj = self.repo.create(obj_in)
        return SubjectResponse.model_validate(obj)

    def update(self, subject_id: int, obj_in: SubjectUpdate) -> SubjectResponse:
        obj = self.repo.get_by_id(subject_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        updated = self.repo.update(obj, obj_in)
        return SubjectResponse.model_validate(updated)

    def delete(self, subject_id: int) -> None:
        obj = self.repo.get_by_id(subject_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        self.repo.delete(subject_id)
