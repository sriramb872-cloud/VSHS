"""
SCHOLARIS ERP - Section Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.section import SectionRepository
from app.schemas.section import SectionCreate, SectionUpdate, SectionResponse


class SectionService:
    def __init__(self, db: Session):
        self.repo = SectionRepository(db)

    def get_by_id(self, section_id: int) -> SectionResponse:
        obj = self.repo.get_by_id(section_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
        return SectionResponse.model_validate(obj)

    def get_by_grade(self, grade_id: int) -> List[SectionResponse]:
        items = self.repo.get_by_grade(grade_id)
        return [SectionResponse.model_validate(i) for i in items]

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[SectionResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [SectionResponse.model_validate(i) for i in items]

    def create(self, obj_in: SectionCreate) -> SectionResponse:
        obj = self.repo.create(obj_in)
        return SectionResponse.model_validate(obj)

    def update(self, section_id: int, obj_in: SectionUpdate) -> SectionResponse:
        obj = self.repo.get_by_id(section_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
        updated = self.repo.update(obj, obj_in)
        return SectionResponse.model_validate(updated)

    def delete(self, section_id: int) -> None:
        obj = self.repo.get_by_id(section_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
        self.repo.delete(section_id)
