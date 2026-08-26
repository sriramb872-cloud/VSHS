"""
SCHOLARIS ERP - Attendance Record Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.attendance_record import AttendanceRecord
from app.crud.attendance_record import crud_attendance_record
from app.schemas.attendance_record import AttendanceRecordCreate, AttendanceRecordUpdate


class AttendanceRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, record_id: int) -> Optional[AttendanceRecord]:
        return crud_attendance_record.get(self.db, record_id)

    def create(self, obj_in: AttendanceRecordCreate, recorded_by_id: Optional[int] = None) -> AttendanceRecord:
        return crud_attendance_record.create(self.db, obj_in, recorded_by_id)

    def update(self, db_obj: AttendanceRecord, obj_in: AttendanceRecordUpdate) -> AttendanceRecord:
        return crud_attendance_record.update(self.db, db_obj, obj_in)

    def delete(self, record_id: int) -> Optional[AttendanceRecord]:
        return crud_attendance_record.delete(self.db, record_id)
