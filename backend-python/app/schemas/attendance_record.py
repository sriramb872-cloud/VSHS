"""
SCHOLARIS ERP - Attendance Record Schemas
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.attendance_record import AttendanceStatus


class AttendanceRecordBase(BaseModel):
    student_id: int
    school_id: int
    date: date
    status: AttendanceStatus
    remarks: Optional[str] = Field(None, max_length=255)


class AttendanceRecordCreate(AttendanceRecordBase):
    pass


class AttendanceRecordUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    remarks: Optional[str] = Field(None, max_length=255)


class AttendanceRecordResponse(AttendanceRecordBase):
    id: int
    recorded_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
