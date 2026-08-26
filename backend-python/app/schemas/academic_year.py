"""
SCHOLARIS ERP - Academic Year Schemas
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class AcademicYearBase(BaseModel):
    name: str = Field(..., max_length=50, description="e.g. 2025-2026")
    start_date: date
    end_date: date
    is_active: bool = False

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class AcademicYearCreate(AcademicYearBase):
    school_id: int


class AcademicYearUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class AcademicYearResponse(AcademicYearBase):
    id: int
    school_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
