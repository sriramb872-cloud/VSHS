# backend-python/app/crud/grade.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Grade


def get_grade(db: Session, grade_id: int) -> Optional[Grade]:
    return db.query(Grade).filter(Grade.id == grade_id).first()


def get_grade_by_name(db: Session, school_id: int, name: str) -> Optional[Grade]:
    return db.query(Grade).filter(
        Grade.school_id == school_id,
        Grade.name == name
    ).first()


def get_grades_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Grade]:
    return db.query(Grade).filter(
        Grade.school_id == school_id
    ).order_by(Grade.display_order).offset(skip).limit(limit).all()


def create_grade(db: Session, school_id: int, data: dict) -> Grade:
    db_item = Grade(school_id=school_id, **data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_grade(db: Session, db_item: Grade, data: dict) -> Grade:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_grade(db: Session, db_item: Grade) -> Grade:
    db.delete(db_item)
    db.commit()
    return db_item
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
