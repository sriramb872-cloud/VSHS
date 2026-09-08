# backend-python/app/routers/v1/teacher_subjects.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User
from app.schemas.teacher_subject import (
    TeacherSubjectCreate,
    TeacherSubjectUpdate,
    TeacherSubjectResponse,
)
from app.services.teacher_subject import TeacherSubjectService

router = APIRouter(prefix="/teacher-subjects", tags=["Teacher Subjects"])


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
    service = TeacherSubjectService(db)
    return service.assign_teacher(payload)


@router.patch("/{assignment_id}", response_model=TeacherSubjectResponse)
def update_teacher_subject_assignment(
    assignment_id: int,
    payload: TeacherSubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    service = TeacherSubjectService(db)
    return service.update_assignment(assignment_id, payload)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_teacher_subject_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    service = TeacherSubjectService(db)
    service.delete_assignment(assignment_id)
    return None
