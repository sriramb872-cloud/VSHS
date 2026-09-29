# backend-python/app/crud/academic_year.py
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import AcademicYear
from app.models.academic_year import AcademicYear as _AcademicYear  # noqa: F401


STATUS_UPCOMING = "UPCOMING"
STATUS_ACTIVE = "ACTIVE"
STATUS_CLOSED = "CLOSED"
STATUS_ARCHIVED = "ARCHIVED"
VALID_STATUSES = (STATUS_UPCOMING, STATUS_ACTIVE, STATUS_CLOSED, STATUS_ARCHIVED)


def get_academic_year(db: Session, academic_year_id: int) -> Optional[AcademicYear]:
    return db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()


def get_academic_year_by_name(db: Session, school_id: int, name: str) -> Optional[AcademicYear]:
    return db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id,
        AcademicYear.name == name
    ).first()


def get_active_academic_year(db: Session, school_id: int) -> Optional[AcademicYear]:
    """The school's ACTIVE year (falls back to the legacy is_current flag)."""
    year = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.school_id == school_id,
            AcademicYear.status == STATUS_ACTIVE,
        )
        .first()
    )
    if year is not None:
        return year
    return (
        db.query(AcademicYear)
        .filter(
            AcademicYear.school_id == school_id,
            AcademicYear.is_active == True,  # noqa: E712
        )
        .first()
    )


def get_academic_years_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[AcademicYear]:
    return (
        db.query(AcademicYear)
        .filter(AcademicYear.school_id == school_id)
        .order_by(AcademicYear.start_date.desc(), AcademicYear.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def find_overlapping_year(
    db: Session,
    school_id: int,
    start_date: date,
    end_date: date,
    exclude_id: Optional[int] = None,
) -> Optional[AcademicYear]:
    """A year in the same school whose date range overlaps the given range."""
    query = db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id,
        AcademicYear.start_date <= end_date,
        AcademicYear.end_date >= start_date,
    )
    if exclude_id is not None:
        query = query.filter(AcademicYear.id != exclude_id)
    return query.first()


def deactivate_other_years(db: Session, school_id: int, keep_id: int) -> None:
    """Clear every other ACTIVE flag/status in the school (single ACTIVE)."""
    db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id,
        AcademicYear.id != keep_id,
        AcademicYear.is_active == True,  # noqa: E712
    ).update({"is_active": False}, synchronize_session=False)
    db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id,
        AcademicYear.id != keep_id,
        AcademicYear.status == STATUS_ACTIVE,
    ).update({AcademicYear.status: STATUS_CLOSED}, synchronize_session=False)
    db.flush()


def create_academic_year(db: Session, school_id: int, data: dict) -> AcademicYear:
    data = {k: v for k, v in data.items() if k != "school_id"}
    data.pop("status", None)
    db_item = AcademicYear(school_id=school_id, **data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_academic_year(db: Session, db_item: AcademicYear, data: dict) -> AcademicYear:
    data.pop("status", None)  # lifecycle changes go through activate/archive
    data.pop("is_active", None)
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_academic_year(db: Session, db_item: AcademicYear) -> AcademicYear:
    db.delete(db_item)
    db.commit()
    return db_item
