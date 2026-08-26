"""
SCHOLARIS ERP - Attendance Repository
"""

from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.schemas.attendance import BulkAttendanceCreate, StudentAttendanceItem


class AttendanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_student_and_date(self, student_id: int, date_val: date) -> Optional[AttendanceRecord]:
        return self.db.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.date == date_val
        ).first()

    def get_records_by_school_and_date(self, school_id: int, date_val: date) -> List[AttendanceRecord]:
        return self.db.query(AttendanceRecord).filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == date_val
        ).all()

    def get_records_by_student(
        self, student_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[AttendanceRecord]:
        query = self.db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id)
        if start_date:
            query = query.filter(AttendanceRecord.date >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.date <= end_date)
        return query.order_by(AttendanceRecord.date.desc()).all()

    def bulk_upsert(self, payload: BulkAttendanceCreate, recorded_by_id: Optional[int] = None) -> List[AttendanceRecord]:
        updated_records = []
        for item in payload.records:
            record = self.get_by_student_and_date(item.student_id, payload.date)
            if record:
                record.status = item.status
                record.remarks = item.remarks
                if recorded_by_id:
                    record.recorded_by_id = recorded_by_id
            else:
                record = AttendanceRecord(
                    student_id=item.student_id,
                    school_id=payload.school_id,
                    date=payload.date,
                    status=item.status,
                    remarks=item.remarks,
                    recorded_by_id=recorded_by_id
                )
            self.db.add(record)
            updated_records.append(record)
        self.db.commit()
        for rec in updated_records:
            self.db.refresh(rec)
        return updated_records
