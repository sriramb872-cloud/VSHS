"""
SCHOLARIS ERP - Upload Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UploadBase(BaseModel):
    filename: str = Field(..., max_length=255)
    original_filename: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=512)
    content_type: str = Field(..., max_length=100)
    file_size: int = Field(..., ge=0)
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[str] = Field(None, max_length=100)


class UploadCreate(UploadBase):
    uploaded_by_id: Optional[int] = None
    school_id: Optional[int] = None


class UploadResponse(UploadBase):
    id: int
    uploaded_by_id: Optional[int] = None
    school_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
