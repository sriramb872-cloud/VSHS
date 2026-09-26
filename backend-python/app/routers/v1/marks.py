# app/routers/v1/marks.py
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import student as student_crud, teacher as teacher_crud
from app.models.exam_subject import ExamSubject
from app.models.section import Section
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher_subject import TeacherSubject
from app.schemas.marks import (
    MarksSubmitPayload,
    FormativeMarksSubmitPayload,
    MarksListResponse,
    MarkResponse,
    StudentMarksViewResponse,
)
from app.services.marks import MarksService
from app.models.user import UserModel
from app.core.audit import write_audit_log

router = APIRouter(prefix="/marks", tags=["Marks"])


@router.get("/", response_model=MarksListResponse)
def list_marks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    exam_id: Optional[int] = None,
    exam_subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    role = str(current_user.role).upper()
    exam_subject_ids: Optional[List[int]] = None

    if role == "STUDENT":
        student = student_crud.get_student_by_user_id(db, current_user.id)
        if not student:
            return {"total": 0, "items": []}
        student_id = student.id
    elif role == "TEACHER":
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            return {"total": 0, "items": []}
        school_id = teacher.school_id

        if exam_subject_id is not None:
            exam_subject = db.query(ExamSubject).filter(ExamSubject.id == exam_subject_id).first()
            if not exam_subject or exam_subject.teacher_id != teacher.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to this exam subject",
                )
            exam_subject_ids = [exam_subject.id]
        elif exam_id is not None:
            exam_subject_ids = [
                row[0]
                for row in db.query(ExamSubject.id)
                .filter(ExamSubject.exam_id == exam_id, ExamSubject.teacher_id == teacher.id)
                .all()
            ]
            if not exam_subject_ids:
                return {"total": 0, "items": []}
        else:
            exam_subject_ids = [
                row[0]
                for row in db.query(ExamSubject.id)
                .filter(ExamSubject.teacher_id == teacher.id)
                .all()
            ]
            if not exam_subject_ids:
                return {"total": 0, "items": []}

        if student_id is not None:
            student = student_crud.get_student(db, student_id)
            if not student:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            enrollment = (
                db.query(StudentEnrollment)
                .filter(StudentEnrollment.student_id == student.id)
                .order_by(StudentEnrollment.created_at.desc(), StudentEnrollment.id.desc())
                .first()
            )
            section = (
                db.query(Section).filter(Section.id == enrollment.section_id).first()
                if enrollment and enrollment.section_id
                else None
            )
            is_class_teacher = bool(section and section.class_teacher_id == teacher.id)
            is_subject_teacher = (
                db.query(TeacherSubject)
                .filter(
                    TeacherSubject.teacher_id == teacher.id,
                    TeacherSubject.section_id == enrollment.section_id,
                )
                .first()
                is not None
                if enrollment and enrollment.section_id
                else False
            )
            if not (is_class_teacher or is_subject_teacher):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to this student's class",
                )

    items, total = MarksService.list_marks(
        db,
        skip=skip,
        limit=limit,
        exam_id=exam_id,
        exam_subject_id=exam_subject_id,
        student_id=student_id,
        school_id=school_id,
        exam_subject_ids=exam_subject_ids,
    )
    return {"total": total, "items": items}


@router.get("/my-marks", response_model=StudentMarksViewResponse)
def get_my_marks(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return MarksService.get_student_marks_view(db, current_user=current_user)


@router.post("/submit", response_model=List[MarkResponse], status_code=status.HTTP_200_OK)
def submit_marks(
    obj_in: MarksSubmitPayload,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    result = MarksService.submit_marks(db, payload=obj_in, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="SUBMIT_MARKS", resource_type="ExamSubject", resource_id=obj_in.exam_subject_id,
        details={"marks_count": len(obj_in.marks)}
    )
    return result


@router.post("/submit-formative", status_code=status.HTTP_200_OK)
def submit_formative_marks(
    obj_in: FormativeMarksSubmitPayload,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    result = MarksService.submit_formative_marks(db, payload=obj_in, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="SUBMIT_FORMATIVE_MARKS", resource_type="ExamSubject", resource_id=obj_in.exam_subject_id,
        details={"marks_count": len(obj_in.marks)}
    )
    return result


@router.post("/", response_model=List[MarkResponse], status_code=status.HTTP_200_OK)
def save_marks(
    obj_in: MarksSubmitPayload,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    result = MarksService.submit_marks(db, payload=obj_in, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="SUBMIT_MARKS", resource_type="ExamSubject", resource_id=obj_in.exam_subject_id,
        details={"marks_count": len(obj_in.marks)}
    )
    return result