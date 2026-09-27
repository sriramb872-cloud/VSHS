# backend-python/app/routers/v1/search.py
"""Global search across the entities the caller is allowed to see.

Two problems this fixes:

1. ``SUPER_ADMIN`` always got empty results. The school-scoped queries were
   inside ``if school_id:``, and a Super Admin has ``school_id = NULL``, so the
   endpoint returned three empty lists no matter what was searched.
2. Only admission numbers, employee IDs and subject names were matched. Student
   and teacher *names* - the thing a user actually types - were not searched,
   and results carried no display name.

Scoping rules:
  * SUPER_ADMIN      -> every school (optionally narrowed with ``school_id``)
  * PRINCIPAL        -> own school only
  * TEACHER          -> own school, own sections only
  * STUDENT          -> own sections only, and self only for the student entity
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.grade import Grade
from app.models.section import Section
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.subject import Subject
from app.models.user import User

router = APIRouter(prefix="/search", tags=["Search"])

_MAX_PER_ENTITY = 25


def _teacher_section_ids(db: Session, user: User) -> List[int]:
    """Sections a teacher may see: class-teacher sections plus subject assignments."""
    teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
    if not teacher:
        return []
    class_teacher = [
        s.id for s in db.query(Section).filter(Section.class_teacher_id == teacher.id).all()
    ]
    subject_teacher = [
        ts.section_id
        for ts in db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher.id).all()
        if ts.section_id
    ]
    return sorted(set(class_teacher) | set(subject_teacher))


def _own_student_id(db: Session, user: User) -> Optional[int]:
    student = db.query(Student).filter(Student.user_id == user.id).first()
    return student.id if student else None


@router.get("")
def global_search(
    q: str = Query(..., min_length=1, description="Free-text query matched against names and identifiers"),
    school_id: Optional[int] = Query(
        None, ge=1, description="Narrow the search to one school (SUPER_ADMIN only)"
    ),
    limit: int = Query(_MAX_PER_ENTITY, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    role = str(current_user.role).upper()
    term = f"%{q.strip()}%"
    limit = min(limit, _MAX_PER_ENTITY)

    # ---------------------------------------------------------------- scope
    scoped_school_id: Optional[int] = current_user.school_id
    if role == "SUPER_ADMIN":
        scoped_school_id = school_id
    else:
        # A non-SUPER_ADMIN may only narrow to their own school. Silently
        # ignoring a foreign `school_id` and returning the caller's own school
        # instead is misleading (it looks like the filter worked), so reject it
        # the same way every other cross-tenant path in this API does.
        if school_id is not None and school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot search another school",
            )

    teacher_section_ids: List[int] = []
    own_student_id: Optional[int] = None
    if role == "TEACHER":
        teacher_section_ids = _teacher_section_ids(db, current_user)
    if role == "STUDENT":
        own_student_id = _own_student_id(db, current_user)
        if own_student_id is None:
            return {"query": q, "students": [], "teachers": [], "subjects": [], "sections": []}

    def apply_school(query, column):
        if role == "SUPER_ADMIN":
            if scoped_school_id is not None:
                query = query.filter(column == scoped_school_id)
        else:
            if scoped_school_id is None:
                return query.filter(False)
            query = query.filter(column == scoped_school_id)
        return query

    # ------------------------------------------------------------- students
    student_query = db.query(Student).join(
        User, User.id == Student.user_id
    ).filter(
        or_(
            Student.admission_number.ilike(term),
            User.display_name.ilike(term),
            User.mobile.ilike(term),
            User.email.ilike(term),
            Student.roll_number.ilike(term),
        )
    )
    student_query = apply_school(student_query, Student.school_id)
    if role == "TEACHER":
        if not teacher_section_ids:
            student_query = student_query.filter(False)
        else:
            student_query = student_query.filter(
                Student.id.in_(
                    db.query(StudentEnrollment.student_id).filter(
                        StudentEnrollment.section_id.in_(teacher_section_ids)
                    )
                )
            )
    elif role == "STUDENT":
        student_query = student_query.filter(Student.id == own_student_id)

    student_rows = student_query.order_by(Student.admission_number).limit(limit).all()
    students = [
        {
            "id": s.id,
            "name": (s.user.display_name if s.user else None) or s.admission_number,
            "admission_number": s.admission_number,
            "roll_number": s.roll_number,
            "school_id": s.school_id,
        }
        for s in student_rows
    ]

    # ------------------------------------------------------------- teachers
    teacher_rows: list = []
    if role in ("SUPER_ADMIN", "PRINCIPAL"):
        teacher_query = db.query(Teacher).join(
            User, User.id == Teacher.user_id
        ).filter(
            or_(
                Teacher.employee_id.ilike(term),
                User.display_name.ilike(term),
                User.mobile.ilike(term),
                User.email.ilike(term),
            )
        )
        teacher_query = apply_school(teacher_query, Teacher.school_id)
        teacher_rows = teacher_query.order_by(Teacher.employee_id).limit(limit).all()
    elif role == "TEACHER":
        # A teacher may look up colleagues, but only inside their own school.
        colleague = (
            db.query(Teacher)
            .join(User, User.id == Teacher.user_id)
            .filter(Teacher.school_id == current_user.school_id, Teacher.id != _own_teacher_id(db, current_user))
            .filter(
                or_(
                    Teacher.employee_id.ilike(term),
                    User.display_name.ilike(term),
                )
            )
            .limit(limit)
            .all()
        )
        teacher_rows = colleague
    teachers = [
        {
            "id": t.id,
            "name": (t.user.display_name if t.user else None) or t.employee_id,
            "employee_id": t.employee_id,
            "school_id": t.school_id,
        }
        for t in teacher_rows
    ]

    # ------------------------------------------------------------- subjects
    subject_rows: list = []
    if role in ("SUPER_ADMIN", "PRINCIPAL"):
        subject_query = db.query(Subject).filter(
            or_(Subject.name.ilike(term), Subject.code.ilike(term))
        )
        subject_query = apply_school(subject_query, Subject.school_id)
        subject_rows = subject_query.order_by(Subject.name).limit(limit).all()
    else:
        # Students and teachers only see subjects they are actually taught.
        if role == "TEACHER":
            own_teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            sub_ids = (
                [ts.subject_id for ts in db.query(TeacherSubject).filter(
                    TeacherSubject.teacher_id == own_teacher.id
                ).all() if ts.subject_id]
                if own_teacher
                else []
            )
        else:
            # A student's taught subjects are the subjects attached to the
            # grades of the sections they are enrolled in.
            # `student_enrollments` has no `grade_id` column and
            # `grade_subjects` is keyed by `grade_id` (it has no `section_id`),
            # so the grade has to be resolved through `sections`.
            student_grade_ids = [
                g
                for (g,) in db.query(Section.grade_id)
                .join(StudentEnrollment, StudentEnrollment.section_id == Section.id)
                .filter(StudentEnrollment.student_id == own_student_id)
                .distinct()
                .all()
            ]
            sub_ids = []
            if student_grade_ids:
                from app.models.grade_subject import GradeSubject

                sub_ids = [
                    gs.subject_id
                    for gs in db.query(GradeSubject)
                    .filter(GradeSubject.grade_id.in_(set(student_grade_ids)))
                    .all()
                    if gs.subject_id
                ]
        if sub_ids:
            subject_rows = (
                db.query(Subject)
                .filter(Subject.id.in_(set(sub_ids)))
                .filter(or_(Subject.name.ilike(term), Subject.code.ilike(term)))
                .order_by(Subject.name)
                .limit(limit)
                .all()
            )
    subjects = [
        {
            "id": s.id,
            "name": s.name,
            "code": getattr(s, "code", None),
            "school_id": s.school_id,
        }
        for s in subject_rows
    ]

    # ------------------------------------------------------------- sections
    section_rows: list = []
    if role in ("SUPER_ADMIN", "PRINCIPAL"):
        section_query = db.query(Section).join(Grade, Grade.id == Section.grade_id).filter(
            or_(Section.name.ilike(term), Grade.name.ilike(term))
        )
        section_query = apply_school(section_query, Section.school_id)
        section_rows = section_query.order_by(Section.name).limit(limit).all()
    elif role == "TEACHER" and teacher_section_ids:
        section_rows = (
            db.query(Section)
            .join(Grade, Grade.id == Section.grade_id)
            .filter(Section.id.in_(teacher_section_ids))
            .filter(or_(Section.name.ilike(term), Grade.name.ilike(term)))
            .limit(limit)
            .all()
        )
    sections = [
        {
            "id": s.id,
            "name": s.name,
            "grade_id": s.grade_id,
            "grade_name": s.grade.name if s.grade else None,
            "school_id": s.school_id,
        }
        for s in section_rows
    ]

    return {
        "query": q,
        "students": students,
        "teachers": teachers,
        "subjects": subjects,
        "sections": sections,
    }


def _own_teacher_id(db: Session, user: User) -> Optional[int]:
    teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
    return teacher.id if teacher else None
