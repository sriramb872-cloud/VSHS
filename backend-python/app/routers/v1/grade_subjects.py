# backend-python/app/routers/v1/grade_subjects.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User
from app.models import GradeSubject

router = APIRouter(prefix="/grade-subjects", tags=["Grade Subjects"])


@router.get("", response_model=List[dict])
def list_grade_subjects(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    items = db.query(GradeSubject).filter(GradeSubject.grade_id == grade_id).all()
    return [
        {
            "id": i.id,
            "grade_id": i.grade_id,
            "subject_id": getattr(i, "subject_id", None)
        }
        for i in items
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def assign_subject_to_grade(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    grade_id = payload.get("grade_id")
    subject_id = payload.get("subject_id")
    if not grade_id or not subject_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="grade_id and subject_id are required")

    existing = db.query(GradeSubject).filter(
        GradeSubject.grade_id == grade_id,
        GradeSubject.subject_id == subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment already exists")

    item = GradeSubject(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "grade_id": item.grade_id,
        "subject_id": getattr(item, "subject_id", None)
    }


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_grade_subject(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    item = db.query(GradeSubject).filter(GradeSubject.id == assignment_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(item)
    db.commit()
    return None