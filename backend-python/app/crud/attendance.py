# backend-python/app/crud/attendance.py
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Attendance

# Writable columns for an attendance row. `remarks` was missing here, so
# `create_attendance` silently discarded it even though the column exists and
# `PATCH /attendance/{id}` allowed updating it.
_VALID_ATTENDANCE_FIELDS = {
    "student_id",
    "section_id",
    "date",
    "status",
    "recorded_by",
    "remarks",
    "academic_year_id",
}


def _year_filter(query, academic_year_id: Optional[int]):
    """Filter by resolved academic year while keeping legacy NULL rows.

    Rows written before ``attendance_records.academic_year_id`` existed have
    NULL there. They are not wrong, just untagged, so they must remain
    visible instead of vanishing when a year is selected.
    """
    if academic_year_id is None:
        return query
    return query.filter(
        (Attendance.academic_year_id == academic_year_id)
        | (Attendance.academic_year_id.is_(None))
    )


def get_attendance(db: Session, attendance_id: int) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.id == attendance_id).first()


def get_student_attendance(
    db: Session, student_id: int, academic_year_id: Optional[int] = None
) -> List[Attendance]:
    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    query = _year_filter(query, academic_year_id)
    return query.all()


def get_attendance_by_date(
    db: Session,
    section_id: int,
    attendance_date: date,
    academic_year_id: Optional[int] = None,
) -> List[Attendance]:
    query = db.query(Attendance).filter(
        Attendance.section_id == section_id,
        Attendance.date == attendance_date,
    )
    query = _year_filter(query, academic_year_id)
    return query.all()


def get_attendance_by_section(
    db: Session,
    section_id: int,
    skip: int = 0,
    limit: int = 100,
    academic_year_id: Optional[int] = None,
) -> List[Attendance]:
    query = db.query(Attendance).filter(Attendance.section_id == section_id)
    query = _year_filter(query, academic_year_id)
    return query.offset(skip).limit(limit).all()


def create_attendance(db: Session, data: dict) -> Attendance:
    data = {k: v for k, v in data.items() if k in _VALID_ATTENDANCE_FIELDS}
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
    # Apply the same whitelist as create_attendance. This used to setattr every
    # key it was handed, so an arbitrary payload could have written to columns
    # that are not part of the attendance contract.
    for key, value in data.items():
        if key in _VALID_ATTENDANCE_FIELDS:
            setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_attendance(db: Session, db_item: Attendance) -> Attendance:
    db.delete(db_item)
    db.commit()
    return db_item
