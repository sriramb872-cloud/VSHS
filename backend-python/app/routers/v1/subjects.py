# backend-python/app/routers/v1/subjects.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import subject as subject_crud
from app.models.user import User
from app.models.teacher_subject import TeacherSubject
from app.models.timetable import Timetable
from app.models.exam_subject import ExamSubject
from app.models.marks import Marks
from app.core.audit import write_audit_log

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
    write_audit_log(
        db, user_id=current_user.id, school_id=subject.school_id,
        action="UPDATE", resource_type="Subject", resource_id=subject.id,
        details={k: str(v) for k, v in payload.items()}
    )
    return {
        "id": updated.id,
        "school_id": updated.school_id,
        "name": getattr(updated, "name", ""),
        "code": getattr(updated, "code", "")
    }


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    subject = subject_crud.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and subject.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    blocking = []
    if getattr(subject, "exam_results", None) and len(subject.exam_results) > 0:
        blocking.append("associated examination results")
    if db.query(TeacherSubject).filter(TeacherSubject.subject_id == subject_id).first():
        blocking.append("teacher assignments")
    if db.query(Timetable).filter(Timetable.subject_id == subject_id).first():
        blocking.append("timetable entries")
    if db.query(ExamSubject).filter(ExamSubject.subject_id == subject_id).first():
        blocking.append("exam schedules")
    if db.query(Marks).join(ExamSubject).filter(ExamSubject.subject_id == subject_id).first():
        blocking.append("recorded marks")
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: this subject has {', '.join(blocking)}. Archive it instead."
        )

    sub_name = getattr(subject, "name", "")
    school_id = subject.school_id
    subject_crud.delete_subject(db, subject)
    write_audit_log(
        db, user_id=current_user.id, school_id=school_id,
        action="DELETE", resource_type="Subject", resource_id=subject_id,
        details={"name": sub_name}
    )
    return None