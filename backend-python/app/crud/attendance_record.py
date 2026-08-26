"""
SCHOLARIS ERP - Attendance Record CRUD
"""

from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.schemas.attendance_record import AttendanceRecordCreate, AttendanceRecordUpdate


class CRUDAttendanceRecord:
    def get(self, db: Session, record_id: int) -> Optional[AttendanceRecord]:
        return db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()

    def get_by_student_and_date(self, db: Session, student_id: int, date_val: date) -> Optional[AttendanceRecord]:
        return db.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.date == date_val
        ).first()

    def get_multi_by_school_and_date(
        self, db: Session, school_id: int, date_val: date, skip: int = 0, limit: int = 100
    ) -> List[AttendanceRecord]:
        return db.query(AttendanceRecord).filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == date_val
        ).offset(skip).limit(limit).all()

    def get_multi_by_student(
        self, db: Session, student_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[AttendanceRecord]:
        query = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id)
        if start_date:
            query = query.filter(AttendanceRecord.date >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.date <= end_date)
        return query.order_by(AttendanceRecord.date.desc()).all()

    def create(self, db: Session, obj_in: AttendanceRecordCreate, recorded_by_id: Optional[int] = None) -> AttendanceRecord:
        db_obj = AttendanceRecord(
            student_id=obj_in.student_id,
            school_id=obj_in.school_id,
            date=obj_in.date,
            status=obj_in.status,
            remarks=obj_in.remarks,
            recorded_by_id=recorded_by_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def upsert(self, db: Session, obj_in: AttendanceRecordCreate, recorded_by_id: Optional[int] = None) -> AttendanceRecord:
        existing = self.get_by_student_and_date(db, student_id=obj_in.student_id, date_val=obj_in.date)
        if existing:
            existing.status = obj_in.status
            existing.remarks = obj_in.remarks
            if recorded_by_id:
                existing.recorded_by_id = recorded_by_id
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing
        return self.create(db, obj_in, recorded_by_id)

    def update(self, db: Session, db_obj: AttendanceRecord, obj_in: AttendanceRecordUpdate) -> AttendanceRecord:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, record_id: int) -> Optional[AttendanceRecord]:
        obj = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


crud_attendance_record = CRUDAttendanceRecord()
