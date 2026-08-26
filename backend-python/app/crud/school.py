# backend-python/app/crud/school.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import School


def get_school(db: Session, school_id: int) -> Optional[School]:
    return db.query(School).filter(School.id == school_id).first()


def get_school_by_code(db: Session, code: str) -> Optional[School]:
    return db.query(School).filter(School.code == code).first()


def get_schools(db: Session, skip: int = 0, limit: int = 100) -> List[School]:
    return db.query(School).offset(skip).limit(limit).all()


def create_school(db: Session, data: dict) -> School:
    db_item = School(**data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_school(db: Session, db_item: School, data: dict) -> School:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_school(db: Session, db_item: School) -> School:
    db.delete(db_item)
    db.commit()
    return db_item
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
