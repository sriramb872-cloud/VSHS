"""
SCHOLARIS ERP - Grade/Class Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GradeBase(BaseModel):
    name: str = Field(..., max_length=50, description="e.g. Grade 10, Class 5")
    code: Optional[str] = Field(None, max_length=20, description="e.g. G10, C5")
    description: Optional[str] = Field(None, max_length=255)


class GradeCreate(GradeBase):
    school_id: int


class GradeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=255)


class GradeResponse(GradeBase):
    id: int
    school_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
