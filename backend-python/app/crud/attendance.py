# backend-python/app/crud/attendance.py
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Attendance


def get_attendance(db: Session, attendance_id: int) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.id == attendance_id).first()


def get_student_attendance(db: Session, student_id: int) -> List[Attendance]:
    return db.query(Attendance).filter(Attendance.student_id == student_id).all()


def get_attendance_by_date(db: Session, section_id: int, attendance_date: date) -> List[Attendance]:
    return db.query(Attendance).filter(
        Attendance.section_id == section_id,
        Attendance.date == attendance_date
    ).all()


def get_attendance_by_section(db: Session, section_id: int, skip: int = 0, limit: int = 100) -> List[Attendance]:
    return db.query(Attendance).filter(
        Attendance.section_id == section_id
    ).offset(skip).limit(limit).all()


def create_attendance(db: Session, data: dict) -> Attendance:
    student_id = data.get("student_id")
    att_date = data.get("date")
    if student_id and att_date:
        existing = db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.date == att_date
        ).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing

    db_item = Attendance(**data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_attendance(db: Session, db_item: Attendance, data: dict) -> Attendance:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_attendance(db: Session, db_item: Attendance) -> Attendance:
    db.delete(db_item)
    db.commit()
    return db_item
