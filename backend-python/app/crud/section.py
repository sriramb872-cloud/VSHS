# backend-python/app/crud/section.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Section


def get_section(db: Session, section_id: int) -> Optional[Section]:
    return db.query(Section).filter(Section.id == section_id).first()


def get_section_by_name(db: Session, grade_id: int, name: str) -> Optional[Section]:
    return db.query(Section).filter(
        Section.grade_id == grade_id,
        Section.name == name
    ).first()


def get_sections_by_grade(db: Session, grade_id: int, skip: int = 0, limit: int = 100) -> List[Section]:
    return db.query(Section).filter(
        Section.grade_id == grade_id
    ).offset(skip).limit(limit).all()


def get_sections_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Section]:
    return db.query(Section).filter(
        Section.school_id == school_id
    ).offset(skip).limit(limit).all()


def create_section(db: Session, school_id: int, data: dict) -> Section:
    db_item = Section(school_id=school_id, **data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_section(db: Session, db_item: Section, data: dict) -> Section:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_section(db: Session, db_item: Section) -> Section:
    db.delete(db_item)
    db.commit()
    return db_item
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
