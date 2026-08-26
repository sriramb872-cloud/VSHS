# backend-python/app/crud/academic_year.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import AcademicYear


def get_academic_year(db: Session, academic_year_id: int) -> Optional[AcademicYear]:
    return db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()


def get_academic_year_by_name(db: Session, school_id: int, name: str) -> Optional[AcademicYear]:
    return db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id,
        AcademicYear.name == name
    ).first()


def get_active_academic_year(db: Session, school_id: int) -> Optional[AcademicYear]:
    return db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id,
        AcademicYear.is_active == True
    ).first()


def get_academic_years_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[AcademicYear]:
    return db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id
    ).offset(skip).limit(limit).all()


def create_academic_year(db: Session, school_id: int, data: dict) -> AcademicYear:
    db_item = AcademicYear(school_id=school_id, **data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_academic_year(db: Session, db_item: AcademicYear, data: dict) -> AcademicYear:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_academic_year(db: Session, db_item: AcademicYear) -> AcademicYear:
    db.delete(db_item)
    db.commit()
    return db_item
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
