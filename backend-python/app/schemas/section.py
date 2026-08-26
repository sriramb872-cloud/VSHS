"""
SCHOLARIS ERP - Section Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SectionBase(BaseModel):
    name: str = Field(..., max_length=50, description="e.g. Section A, B, Alpha")
    capacity: Optional[int] = Field(None, ge=1, le=200)


class SectionCreate(SectionBase):
    grade_id: int
    school_id: int


class SectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=200)


class SectionResponse(SectionBase):
    id: int
    grade_id: int
    school_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
