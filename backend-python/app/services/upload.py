"""
SCHOLARIS ERP - Upload Service
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.upload import UploadRepository
from app.schemas.upload import UploadCreate, UploadResponse


class UploadService:
    def __init__(self, db: Session):
        self.repo = UploadRepository(db)

    def get_by_id(self, upload_id: int) -> UploadResponse:
        obj = self.repo.get_by_id(upload_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload metadata not found")
        return UploadResponse.model_validate(obj)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[UploadResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [UploadResponse.model_validate(i) for i in items]

    def create_metadata(self, obj_in: UploadCreate) -> UploadResponse:
        obj = self.repo.create(obj_in)
        return UploadResponse.model_validate(obj)

    def delete(self, upload_id: int) -> None:
        obj = self.repo.get_by_id(upload_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload metadata not found")
        self.repo.delete(upload_id)
