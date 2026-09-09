# app/routers/v1/homework.py
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.homework import (
    HomeworkCreate,
    HomeworkListResponse,
    HomeworkResponse,
    HomeworkUpdate,
)
from app.services.homework import HomeworkService
from app.models.user import UserModel
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.homework import Homework
from app.models.subject import Subject
from app.models.grade import Grade
from app.models.section import Section

def _enrich_with_names(db: Session, items):
    single = not isinstance(items, list)
    homework_list = [items] if single else items
    if not homework_list:
        return items

    subject_ids = {h.subject_id for h in homework_list if h.subject_id}
    grade_ids = {h.grade_id for h in homework_list if h.grade_id}
    section_ids = {h.section_id for h in homework_list if h.section_id}

    subjects = {s.id: s.name for s in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()} if subject_ids else {}
    grades = {g.id: g.name for g in db.query(Grade).filter(Grade.id.in_(grade_ids)).all()} if grade_ids else {}
    sections = {s.id: s.name for s in db.query(Section).filter(Section.id.in_(section_ids)).all()} if section_ids else {}

    for h in homework_list:
        h.subject_name = subjects.get(h.subject_id)
        h.grade_name = grades.get(h.grade_id)
        h.section_name = sections.get(h.section_id)

    return homework_list[0] if single else homework_list

router = APIRouter(prefix="/homework", tags=["Homework"])


@router.get("/", response_model=HomeworkListResponse)
def list_homework(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    academic_year_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    due_date: Optional[date] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    items, total = HomeworkService.list_homework(
        db,
        skip=skip,
        limit=limit,
        academic_year_id=academic_year_id,
        grade_id=grade_id,
        section_id=section_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        due_date=due_date,
        current_user=current_user,
    )
    items = _enrich_with_names(db, items)
    return {"total": total, "items": items}

@router.get("/{homework_id}", response_model=HomeworkResponse)
def get_homework_by_id(
    homework_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    homework = HomeworkService.get_homework(db, homework_id=homework_id, current_user=current_user)
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found",
        )
    return _enrich_with_names(db, homework)

@router.post("/", response_model=HomeworkResponse, status_code=status.HTTP_201_CREATED)
def create_homework(
    obj_in: HomeworkCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    teacher = getattr(current_user, "teacher_profile", None) or (
        db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    )
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher profile not found for user",
        )
    if str(current_user.role).upper() == "TEACHER":
        ts = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == teacher.id,
            TeacherSubject.subject_id == obj_in.subject_id,
            TeacherSubject.grade_id == obj_in.grade_id,
            TeacherSubject.section_id == obj_in.section_id,
        ).first()
        if not ts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher is not assigned to this subject/grade/section",
            )
    school_id = current_user.school_id or teacher.school_id
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School context not found",
        )
    return HomeworkService.create_homework(
        db, obj_in=obj_in, teacher_id=teacher.id, school_id=school_id
    )

@router.patch("/{homework_id}", response_model=HomeworkResponse)
def update_homework(
    homework_id: int,
    obj_in: HomeworkUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    teacher_id = None
    if str(current_user.role).upper() == "TEACHER":
        teacher = getattr(current_user, "teacher_profile", None) or (
            db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        )
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher profile not found",
            )
        teacher_id = teacher.id
        existing = db.query(Homework).filter(Homework.id == homework_id).first()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Homework not found",
            )
        new_subject_id = obj_in.subject_id if obj_in.subject_id is not None else existing.subject_id
        new_grade_id = obj_in.grade_id if obj_in.grade_id is not None else existing.grade_id
        new_section_id = obj_in.section_id if obj_in.section_id is not None else existing.section_id
        if (
            (obj_in.subject_id is not None and obj_in.subject_id != existing.subject_id)
            or (obj_in.grade_id is not None and obj_in.grade_id != existing.grade_id)
            or (obj_in.section_id is not None and obj_in.section_id != existing.section_id)
        ):
            ts = db.query(TeacherSubject).filter(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.subject_id == new_subject_id,
                TeacherSubject.grade_id == new_grade_id,
                TeacherSubject.section_id == new_section_id,
            ).first()
            if not ts:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Teacher is not assigned to this subject/grade/section",
                )
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    homework = HomeworkService.update_homework(
        db, homework_id=homework_id, obj_in=obj_in, teacher_id=teacher_id, school_id=school_id
    )
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found or unauthorized to edit",
        )
    return homework

@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_homework(
    homework_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    teacher_id = None
    if str(current_user.role).upper() == "TEACHER":
        teacher = getattr(current_user, "teacher_profile", None) or (
            db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        )
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher profile not found",
            )
        teacher_id = teacher.id
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    success = HomeworkService.delete_homework(
        db, homework_id=homework_id, teacher_id=teacher_id, school_id=school_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found or unauthorized to delete",
        )
    return None