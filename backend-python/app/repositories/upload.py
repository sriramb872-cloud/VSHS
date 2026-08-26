"""
SCHOLARIS ERP - Upload Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.upload import Upload
from app.crud.upload import crud_upload
from app.schemas.upload import UploadCreate


class UploadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, upload_id: int) -> Optional[Upload]:
        return crud_upload.get(self.db, upload_id)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[Upload]:
        return crud_upload.get_multi_by_school(self.db, school_id, skip, limit)

    def get_by_entity(self, entity_type: str, entity_id: str) -> List[Upload]:
        return crud_upload.get_multi_by_entity(self.db, entity_type, entity_id)

    def create(self, obj_in: UploadCreate) -> Upload:
        return crud_upload.create(self.db, obj_in)

    def delete(self, upload_id: int) -> Optional[Upload]:
        return crud_upload.delete(self.db, upload_id)
