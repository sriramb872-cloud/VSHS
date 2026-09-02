# backend-python/app/routers/v1/student_enrollments.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import student_enrollment as se_crud, teacher as teacher_crud, student as student_crud
from app.models.student_enrollment import StudentEnrollment
from app.models.section import Section
from app.models.student import Student
from app.models.user import User

router = APIRouter(prefix="/student-enrollments", tags=["Student Enrollments"])


def serialize_enrollment(e: StudentEnrollment, attendance_pct: float = None) -> dict:
    student = e.student
    user = student.user if student else None
    grade_id = None
    grade_name = None
    section_name = None
    if e.section:
        section_name = getattr(e.section, "name", None) or getattr(e.section, "section_name", None)
        grade_id = e.section.grade_id
        if e.section.grade:
            grade_name = getattr(e.section.grade, "name", None) or getattr(e.section.grade, "grade_name", None)

    academic_year_name = None
    if e.academic_year:
        academic_year_name = getattr(e.academic_year, "name", None) or getattr(e.academic_year, "year_name", None)

    return {
        "id": e.id,
        "enrollment_id": e.id,
        "student_id": e.student_id,
        "student_name": user.display_name if user else None,
        "full_name": user.display_name if user else None,
        "admission_number": getattr(student, "admission_number", None) if student else None,
        "roll_number": e.roll_number or (getattr(student, "roll_number", None) if student else None),
        "gender": getattr(student, "gender", None) if student else None,
        "grade_id": grade_id,
        "grade_name": grade_name,
        "section_id": e.section_id,
        "section_name": section_name,
        "academic_year_id": e.academic_year_id,
        "academic_year_name": academic_year_name,
        "attendance_percentage": attendance_pct,
        "created_at": getattr(e, "created_at", None),
    }


@router.get("", response_model=List[dict])
def list_enrollments(
    academic_year_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    school_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_role = str(current_user.role).upper()

    if user_role == "TEACHER":
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            return []
        assigned_sec = db.query(Section).filter(
            Section.class_teacher_id == teacher.id,
            Section.school_id == teacher.school_id
        ).first()
        if not assigned_sec:
            return []

        items, attendance_map = se_crud.get_enrollments(
            db,
            school_id=teacher.school_id,
            academic_year_id=academic_year_id,
            grade_id=None,
            section_id=assigned_sec.id,
            skip=skip,
            limit=limit
        )
        return [serialize_enrollment(i, attendance_map.get(i.student_id)) for i in items]

    target_school_id = current_user.school_id
    if user_role == "SUPER_ADMIN" and school_id:
        target_school_id = school_id

    if not target_school_id and user_role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    items, attendance_map = se_crud.get_enrollments(
        db,
        school_id=target_school_id,
        academic_year_id=academic_year_id,
        grade_id=grade_id,
        section_id=section_id,
        skip=skip,
        limit=limit
    )

    return [serialize_enrollment(i, attendance_map.get(i.student_id)) for i in items]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def enroll_student(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    user_role = str(current_user.role).upper()
    data = dict(payload)

    if user_role == "TEACHER":
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")
        assigned_sec = db.query(Section).filter(
            Section.class_teacher_id == teacher.id,
            Section.school_id == teacher.school_id
        ).first()
        if not assigned_sec:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned as a Class Teacher.")

        student_id = data.get("student_id")
        if not student_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="student_id is required")
        student = student_crud.get_student(db, int(student_id))
        if not student or student.school_id != teacher.school_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found in your school")

        data["section_id"] = assigned_sec.id
    else:
        student_id = data.get("student_id")

    academic_year_id = data.get("academic_year_id")
    if student_id and academic_year_id:
        existing = se_crud.get_student_enrollment_by_academic_year(db, int(student_id), int(academic_year_id))
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student already enrolled for this academic year")

    item = se_crud.create_student_enrollment(db, data)
    return serialize_enrollment(item)


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    item = se_crud.get_student_enrollment(db, enrollment_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    if str(current_user.role).upper() != "SUPER_ADMIN":
        if item.student and item.student.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    se_crud.delete_student_enrollment(db, item)
    return None