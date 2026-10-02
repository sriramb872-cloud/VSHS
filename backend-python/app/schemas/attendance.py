"""
SCHOLARIS ERP - Attendance Schemas
"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.attendance_record import AttendanceStatus


class AttendanceCreate(BaseModel):
    student_id: int
    section_id: Optional[int] = None
    date: date
    status: AttendanceStatus
    recorded_by: Optional[int] = None
    # Persisted on the `attendance_records.remarks` column. It used to be
    # dropped silently: the column existed and PATCH /attendance/{id} accepted
    # it, but the create schema had no such field and crud's whitelist dropped
    # it too, so create/update behaved differently for the same input.
    remarks: Optional[str] = Field(None, max_length=255)


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
