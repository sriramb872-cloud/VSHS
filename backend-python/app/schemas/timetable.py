# app/schemas/timetable.py
from datetime import time
from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field


class TimetableItemResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    academic_year_id: Optional[int] = None
    grade_id: int
    grade_name: Optional[str] = None
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None
    day_of_week: Optional[str] = "Monday"
    start_time: str
    end_time: str
    room_number: Optional[str] = None
    period_number: Optional[int] = None

    class Config:
        from_attributes = True


TimetableResponse = TimetableItemResponse
TimetableSlotResponse = TimetableItemResponse


class TimetableEntryBase(BaseModel):
    day_of_week: str = Field("Monday", description="Day of the week e.g., Monday, Tuesday")
    period_number: Optional[int] = Field(None, ge=1, description="Period number")
    start_time: str = Field(..., description="Start time of the period")
    end_time: str = Field(..., description="End time of the period")
    subject_id: int = Field(..., description="Subject ID")
    teacher_id: int = Field(..., description="Teacher ID")
    classroom: Optional[str] = Field(None, description="Classroom identifier/name")


class TimetableEntryCreate(TimetableEntryBase):
    pass


class TimetableCreate(BaseModel):
    grade_id: int
    subject_id: int
    teacher_id: int
    start_time: str
    end_time: str
    day_of_week: Optional[str] = "Monday"
    academic_year_id: Optional[int] = None
    section_id: Optional[int] = None
    room_number: Optional[str] = None
    period_number: Optional[int] = None
    entries: Optional[List[TimetableEntryCreate]] = None


class TimetableUpdate(BaseModel):
    grade_id: Optional[int] = None
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    day_of_week: Optional[str] = None
    academic_year_id: Optional[int] = None
    section_id: Optional[int] = None
    room_number: Optional[str] = None
    period_number: Optional[int] = None


class TimetableCopy(BaseModel):
    target_section_id: Optional[int] = None
    target_grade_id: Optional[int] = None


class TimetableListResponse(BaseModel):
    total: int
    items: List[TimetableItemResponse]

