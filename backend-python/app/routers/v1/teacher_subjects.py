# backend-python/app/routers/v1/teacher_subjects.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User
from app.models.teacher import Teacher
from app.models.subject import Subject
from app.schemas.teacher_subject import (
    TeacherSubjectCreate,
    TeacherSubjectUpdate,
    TeacherSubjectResponse,
)
from app.services.teacher_subject import TeacherSubjectService
from app.core.audit import write_audit_log

router = APIRouter(prefix="/teacher-subjects", tags=["Teacher Subjects"])


def _authorize_assignment_school(db: Session, assignment_id: int, current_user: User):
    service = TeacherSubjectService(db)
    assignment = service.repo.get_by_id(assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
    if str(current_user.role).upper() != "SUPER_ADMIN" and assignment.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return assignment


def _validate_assignment_relationships(db: Session, teacher_id: int, subject_id: int, school_id: int):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not teacher or teacher.school_id != school_id or not subject or subject.school_id != school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher and subject must belong to the assignment school")


@router.get("", response_model=List[TeacherSubjectResponse])
def list_teacher_subjects(
    teacher_id: Optional[int] = Query(None, description="Filter by teacher"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TeacherSubjectService(db)
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None

    if teacher_id is not None:
        return service.get_by_teacher(teacher_id, school_id=school_id)

    if not school_id:
        return []
    return service.get_by_school(school_id, skip=skip, limit=limit)


@router.post("", response_model=TeacherSubjectResponse, status_code=status.HTTP_201_CREATED)
def assign_teacher_to_subject(
    payload: TeacherSubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    if str(current_user.role).upper() == "PRINCIPAL":
        payload = TeacherSubjectCreate(
            **{**payload.model_dump(), "school_id": current_user.school_id}
        )
    _validate_assignment_relationships(db, payload.teacher_id, payload.subject_id, payload.school_id)
    service = TeacherSubjectService(db)
    return service.assign_teacher(payload)


@router.patch("/{assignment_id}", response_model=TeacherSubjectResponse)
def update_teacher_subject_assignment(
    assignment_id: int,
    payload: TeacherSubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    assignment = _authorize_assignment_school(db, assignment_id, current_user)
    if str(current_user.role).upper() == "PRINCIPAL":
        update_data = payload.model_dump(exclude_unset=True)
        update_data.pop("school_id", None)
        payload = TeacherSubjectUpdate(**update_data)
    school_id = assignment.school_id
    teacher_id = payload.teacher_id if payload.teacher_id is not None else assignment.teacher_id
    subject_id = payload.subject_id if payload.subject_id is not None else assignment.subject_id
    _validate_assignment_relationships(db, teacher_id, subject_id, school_id)
    service = TeacherSubjectService(db)
    result = service.update_assignment(assignment_id, payload)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id or school_id,
        action="UPDATE", resource_type="TeacherSubject", resource_id=assignment_id, details={}
    )
    return result


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_teacher_subject_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    assignment = _authorize_assignment_school(db, assignment_id, current_user)
    service = TeacherSubjectService(db)
    service.delete_assignment(assignment_id)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id or getattr(assignment, "school_id", None),
        action="DELETE", resource_type="TeacherSubject", resource_id=assignment_id, details={}
    )
    return None

