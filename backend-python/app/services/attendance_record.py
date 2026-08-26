"""
SCHOLARIS ERP - Attendance Record Service
"""

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.attendance_record import AttendanceRecordRepository
from app.schemas.attendance_record import AttendanceRecordCreate, AttendanceRecordUpdate, AttendanceRecordResponse


class AttendanceRecordService:
    def __init__(self, db: Session):
        self.repo = AttendanceRecordRepository(db)

    def get_by_id(self, record_id: int) -> AttendanceRecordResponse:
        rec = self.repo.get_by_id(record_id)
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
        return AttendanceRecordResponse.model_validate(rec)

    def create(self, obj_in: AttendanceRecordCreate, recorded_by_id: Optional[int] = None) -> AttendanceRecordResponse:
        rec = self.repo.create(obj_in, recorded_by_id=recorded_by_id)
        return AttendanceRecordResponse.model_validate(rec)

    def update(self, record_id: int, obj_in: AttendanceRecordUpdate) -> AttendanceRecordResponse:
        rec = self.repo.get_by_id(record_id)
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
        updated = self.repo.update(rec, obj_in)
        return AttendanceRecordResponse.model_validate(updated)

    def delete(self, record_id: int) -> None:
        rec = self.repo.get_by_id(record_id)
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
        self.repo.delete(record_id)
