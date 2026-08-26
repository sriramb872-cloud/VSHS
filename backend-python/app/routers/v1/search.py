# backend-python/app/routers/v1/search.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.subject import Subject
from app.models.user import User

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=dict)
def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    school_id = current_user.school_id
    if not school_id and str(current_user.role).upper() != "SUPER_ADMIN":
        return {"students": [], "teachers": [], "subjects": []}

    students = []
    teachers = []
    subjects = []

    if school_id:
        q_lower = q.lower()

        student_rows = db.query(Student).filter(
            Student.school_id == school_id,
            Student.admission_number.ilike(f"%{q}%")
        ).limit(50).all()
        students = [{"id": s.id, "admission_number": getattr(s, "admission_number", "")} for s in student_rows]

        teacher_rows = db.query(Teacher).filter(
            Teacher.school_id == school_id,
            Teacher.employee_id.ilike(f"%{q}%")
        ).limit(50).all()
        teachers = [{"id": t.id, "employee_id": getattr(t, "employee_id", "")} for t in teacher_rows]

        subject_rows = db.query(Subject).filter(
            Subject.school_id == school_id,
            Subject.name.ilike(f"%{q}%")
        ).limit(50).all()
        subjects = [{"id": sub.id, "name": getattr(sub, "name", "")} for sub in subject_rows]

    return {
        "students": students,
        "teachers": teachers,
        "subjects": subjects
    }