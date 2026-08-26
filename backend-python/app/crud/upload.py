"""
SCHOLARIS ERP - Upload CRUD
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.upload import Upload
from app.schemas.upload import UploadCreate


class CRUDUpload:
    def get(self, db: Session, upload_id: int) -> Optional[Upload]:
        return db.query(Upload).filter(Upload.id == upload_id).first()

    def get_multi_by_school(
        self, db: Session, school_id: int, skip: int = 0, limit: int = 100
    ) -> List[Upload]:
        return db.query(Upload).filter(Upload.school_id == school_id).offset(skip).limit(limit).all()

    def get_multi_by_entity(
        self, db: Session, entity_type: str, entity_id: str
    ) -> List[Upload]:
        return db.query(Upload).filter(
            Upload.entity_type == entity_type,
            Upload.entity_id == entity_id
        ).all()

    def create(self, db: Session, obj_in: UploadCreate) -> Upload:
        db_obj = Upload(
            filename=obj_in.filename,
            original_filename=obj_in.original_filename,
            file_path=obj_in.file_path,
            content_type=obj_in.content_type,
            file_size=obj_in.file_size,
            entity_type=obj_in.entity_type,
            entity_id=obj_in.entity_id,
            uploaded_by_id=obj_in.uploaded_by_id,
            school_id=obj_in.school_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, upload_id: int) -> Optional[Upload]:
        obj = db.query(Upload).filter(Upload.id == upload_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


crud_upload = CRUDUpload()
