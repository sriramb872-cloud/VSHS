# backend-python/app/crud/exam_result.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import ExamResult


def get_exam_result(db: Session, result_id: int) -> Optional[ExamResult]:
    return db.query(ExamResult).filter(ExamResult.id == result_id).first()


def get_exam_result_by_unique(db: Session, exam_id: int, student_id: int, subject_id: int) -> Optional[ExamResult]:
    return db.query(ExamResult).filter(
        ExamResult.exam_id == exam_id,
        ExamResult.student_id == student_id,
        ExamResult.subject_id == subject_id
    ).first()


def get_results_for_student(db: Session, student_id: int, exam_id: Optional[int] = None) -> List[ExamResult]:
    query = db.query(ExamResult).filter(ExamResult.student_id == student_id)
    if exam_id:
        query = query.filter(ExamResult.exam_id == exam_id)
    return query.all()


def get_results_for_exam(db: Session, exam_id: int, skip: int = 0, limit: int = 100) -> List[ExamResult]:
    return db.query(ExamResult).filter(
        ExamResult.exam_id == exam_id
    ).offset(skip).limit(limit).all()


def get_results_for_subject(db: Session, subject_id: int, skip: int = 0, limit: int = 100) -> List[ExamResult]:
    return db.query(ExamResult).filter(
        ExamResult.subject_id == subject_id
    ).offset(skip).limit(limit).all()


def create_exam_result(db: Session, data: dict) -> ExamResult:
    db_item = ExamResult(**data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_exam_result(db: Session, db_item: ExamResult, data: dict) -> ExamResult:
    for key, value in data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_exam_result(db: Session, db_item: ExamResult) -> ExamResult:
    db.delete(db_item)
    db.commit()
    return db_item
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
