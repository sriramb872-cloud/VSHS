"""
SCHOLARIS ERP - Grade Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.grade import GradeRepository
from app.schemas.grade import GradeCreate, GradeUpdate, GradeResponse


class GradeService:
    def __init__(self, db: Session):
        self.repo = GradeRepository(db)

    def get_by_id(self, grade_id: int) -> GradeResponse:
        obj = self.repo.get_by_id(grade_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
        return GradeResponse.model_validate(obj)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[GradeResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [GradeResponse.model_validate(i) for i in items]

    def create(self, obj_in: GradeCreate) -> GradeResponse:
        obj = self.repo.create(obj_in)
        return GradeResponse.model_validate(obj)

    def update(self, grade_id: int, obj_in: GradeUpdate) -> GradeResponse:
        obj = self.repo.get_by_id(grade_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
        updated = self.repo.update(obj, obj_in)
        return GradeResponse.model_validate(updated)

    def delete(self, grade_id: int) -> None:
        obj = self.repo.get_by_id(grade_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
        self.repo.delete(grade_id)
