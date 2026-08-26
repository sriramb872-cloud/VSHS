"""
SCHOLARIS ERP - Academic Year Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.academic_year import AcademicYearRepository
from app.schemas.academic_year import AcademicYearCreate, AcademicYearUpdate, AcademicYearResponse


class AcademicYearService:
    def __init__(self, db: Session):
        self.repo = AcademicYearRepository(db)

    def get_by_id(self, academic_year_id: int) -> AcademicYearResponse:
        obj = self.repo.get_by_id(academic_year_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
        return AcademicYearResponse.model_validate(obj)

    def get_active(self, school_id: int) -> AcademicYearResponse:
        obj = self.repo.get_active_for_school(school_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active academic year found for school")
        return AcademicYearResponse.model_validate(obj)

    def get_all(self, school_id: int, skip: int = 0, limit: int = 100) -> List[AcademicYearResponse]:
        items = self.repo.get_all_by_school(school_id, skip, limit)
        return [AcademicYearResponse.model_validate(i) for i in items]

    def create(self, obj_in: AcademicYearCreate) -> AcademicYearResponse:
        if obj_in.is_active:
            active = self.repo.get_active_for_school(obj_in.school_id)
            if active:
                self.repo.update(active, AcademicYearUpdate(is_active=False))
        obj = self.repo.create(obj_in)
        return AcademicYearResponse.model_validate(obj)

    def update(self, academic_year_id: int, obj_in: AcademicYearUpdate) -> AcademicYearResponse:
        obj = self.repo.get_by_id(academic_year_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
        if obj_in.is_active is True:
            active = self.repo.get_active_for_school(obj.school_id)
            if active and active.id != academic_year_id:
                self.repo.update(active, AcademicYearUpdate(is_active=False))
        updated = self.repo.update(obj, obj_in)
        return AcademicYearResponse.model_validate(updated)

    def delete(self, academic_year_id: int) -> None:
        obj = self.repo.get_by_id(academic_year_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
        self.repo.delete(academic_year_id)
