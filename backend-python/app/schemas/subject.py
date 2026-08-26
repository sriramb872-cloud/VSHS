"""
SCHOLARIS ERP - Subject Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SubjectBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    description: Optional[str] = Field(None, max_length=255)
    is_elective: bool = False


class SubjectCreate(SubjectBase):
    school_id: int
    grade_id: Optional[int] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=255)
    is_elective: Optional[bool] = None
    grade_id: Optional[int] = None


class SubjectResponse(SubjectBase):
    id: int
    school_id: int
    grade_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
