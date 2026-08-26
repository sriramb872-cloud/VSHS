# backend-python/app/crud/subject.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Subject


def get_subject(db: Session, subject_id: int) -> Optional[Subject]:
    return db.query(Subject).filter(Subject.id == subject_id).first()


def get_subject_by_name(db: Session, school_id: int, name: str) -> Optional[Subject]:
    return db.query(Subject).filter(
        Subject.school_id == school_id,
        Subject.name == name
    ).first()


def get_subjects_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Subject]:
    return db.query(Subject).filter(
        Subject.school_id == school_id
    ).offset(skip).limit(limit).all()


def create_subject(db: Session, school_id: int, data: dict) -> Subject:
    db_item = Subject(school_id=school_id, **data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_subject(db: Session, db_item: Subject, data: dict) -> Subject:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_subject(db: Session, db_item: Subject) -> Subject:
    db.delete(db_item)
    db.commit()
    return db_item
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
