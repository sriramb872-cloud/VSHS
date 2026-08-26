"""
SCHOLARIS ERP - Attendance Schemas
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.attendance_record import AttendanceStatus


class AttendanceCreate(BaseModel):
    student_id: int
    section_id: Optional[int] = None
    date: date
    status: str
    remarks: Optional[str] = None
    recorded_by: Optional[int] = None


class StudentAttendanceItem(BaseModel):
    student_id: int
    status: AttendanceStatus
    remarks: Optional[str] = Field(None, max_length=255)


class BulkAttendanceCreate(BaseModel):
    school_id: int
    date: date
    records: List[StudentAttendanceItem]


class AttendanceSummary(BaseModel):
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    attendance_rate: float
