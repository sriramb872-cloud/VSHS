"""
SCHOLARIS ERP - Attendance Service
"""

from datetime import date
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.attendance import AttendanceRepository
from app.schemas.attendance import BulkAttendanceCreate, AttendanceSummary
from app.schemas.attendance_record import AttendanceRecordResponse
from app.models.attendance_record import AttendanceStatus


class AttendanceService:
    def __init__(self, db: Session):
        self.repo = AttendanceRepository(db)

    def mark_bulk_attendance(
        self, payload: BulkAttendanceCreate, recorded_by_id: Optional[int] = None
    ) -> List[AttendanceRecordResponse]:
        records = self.repo.bulk_upsert(payload, recorded_by_id=recorded_by_id)
        return [AttendanceRecordResponse.model_validate(r) for r in records]

    def get_daily_summary(self, school_id: int, date_val: date) -> AttendanceSummary:
        records = self.repo.get_records_by_school_and_date(school_id, date_val)
        total = len(records)
        if total == 0:
            return AttendanceSummary(
                total_students=0,
                present_count=0,
                absent_count=0,
                late_count=0,
                excused_count=0,
                attendance_rate=0.0
            )

        present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
        late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        excused = sum(1 for r in records if r.status == AttendanceStatus.EXCUSED)
        rate = round(((present + late) / total) * 100.0, 2)

        return AttendanceSummary(
            total_students=total,
            present_count=present,
            absent_count=absent,
            late_count=late,
            excused_count=excused,
            attendance_rate=rate
        )

    def get_student_attendance(
        self, student_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[AttendanceRecordResponse]:
        records = self.repo.get_records_by_student(student_id, start_date, end_date)
        return [AttendanceRecordResponse.model_validate(r) for r in records]
