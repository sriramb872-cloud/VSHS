# backend-python/app/routers/v1/subjects.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import subject as subject_crud
from app.models.user import User

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", response_model=List[dict])
def list_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    subjects = subject_crud.get_subjects_by_school(db, school_id=school_id, skip=skip, limit=limit)
    return [
        {
            "id": s.id,
            "school_id": s.school_id,
            "name": getattr(s, "name", ""),
            "code": getattr(s, "code", "")
        }
        for s in subjects
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    name = payload.get("name")
    if name and subject_crud.get_subject_by_name(db, school_id, name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject already exists")

    subject = subject_crud.create_subject(db, school_id, payload)
    return {
        "id": subject.id,
        "school_id": subject.school_id,
        "name": getattr(subject, "name", ""),
        "code": getattr(subject, "code", "")
    }


@router.get("/{subject_id}", response_model=dict)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    subject = subject_crud.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and subject.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return {
        "id": subject.id,
        "school_id": subject.school_id,
        "name": getattr(subject, "name", ""),
        "code": getattr(subject, "code", "")
    }


@router.patch("/{subject_id}", response_model=dict)
def update_subject(
    subject_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    subject = subject_crud.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and subject.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    updated = subject_crud.update_subject(db, subject, payload)
    return {
        "id": updated.id,
        "school_id": updated.school_id,
        "name": getattr(updated, "name", ""),
        "code": getattr(updated, "code", "")
    }