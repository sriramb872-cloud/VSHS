# backend-python/app/routers/v1/sections.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import section as section_crud, grade as grade_crud
from app.models.user import User
from app.models.teacher import Teacher
from app.models.attendance import Attendance
from app.models.timetable import Timetable
from app.models.exam import Exam
from app.core.audit import write_audit_log

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("", response_model=List[dict])
def list_sections(
    grade_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    if grade_id:
        grade = grade_crud.get_grade(db, grade_id)
        if not grade or grade.school_id != school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Grade does not belong to your school")
        sections = section_crud.get_sections_by_grade(db, grade_id=grade_id, skip=skip, limit=limit)
    else:
        sections = section_crud.get_sections_by_school(db, school_id=school_id, skip=skip, limit=limit)

    return [
        {
            "id": s.id,
            "school_id": s.school_id,
            "grade_id": s.grade_id,
            "name": getattr(s, "name", ""),
            "grade_name": getattr(s.grade, "name", "") if getattr(s, "grade", None) else f"Class {s.grade_id}",
            "class_teacher_id": getattr(s, "class_teacher_id", None),
            "class_teacher_name": (
                s.class_teacher.user.display_name
                if getattr(s, "class_teacher", None) and getattr(s.class_teacher, "user", None)
                else None
            ),
        }
        for s in sections
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_section(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    grade_id = payload.get("grade_id")
    if not grade_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="grade_id is required")

    grade = grade_crud.get_grade(db, grade_id)
    if not grade or grade.school_id != school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade reference")

    section = section_crud.create_section(db, school_id, payload)
    return {
        "id": section.id,
        "school_id": section.school_id,
        "grade_id": section.grade_id,
        "name": getattr(section, "name", "")
    }


@router.get("/{section_id}", response_model=dict)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    section = section_crud.get_section(db, section_id)
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and section.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return {
        "id": section.id,
        "school_id": section.school_id,
        "grade_id": section.grade_id,
        "name": getattr(section, "name", "")
    }


@router.patch("/{section_id}", response_model=dict)
def update_section(
    section_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    section = section_crud.get_section(db, section_id)
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and section.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if "grade_id" in payload and payload["grade_id"]:
        grade = grade_crud.get_grade(db, int(payload["grade_id"]))
        if not grade or (str(current_user.role).upper() != "SUPER_ADMIN" and grade.school_id != current_user.school_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to your school")

    if "class_teacher_id" in payload and payload["class_teacher_id"]:
        teacher = db.query(Teacher).filter(Teacher.id == int(payload["class_teacher_id"])).first()
        if not teacher or (str(current_user.role).upper() != "SUPER_ADMIN" and teacher.school_id != current_user.school_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Class teacher does not belong to your school")

    updated = section_crud.update_section(db, section, payload)
    write_audit_log(
        db, user_id=current_user.id, school_id=section.school_id,
        action="UPDATE", resource_type="Section", resource_id=section.id,
        details={k: str(v) for k, v in payload.items()}
    )
    return {
        "id": updated.id,
        "school_id": updated.school_id,
        "grade_id": updated.grade_id,
        "name": getattr(updated, "name", ""),
        "class_teacher_id": getattr(updated, "class_teacher_id", None)
    }


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    section = section_crud.get_section(db, section_id)
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and section.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    blocking = []
    if getattr(section, "enrollments", None) and len(section.enrollments) > 0:
        blocking.append("student enrollments")
    if db.query(Attendance).filter(Attendance.section_id == section_id).first():
        blocking.append("attendance records")
    if db.query(Timetable).filter(Timetable.section_id == section_id).first():
        blocking.append("timetable entries")
    if db.query(Exam).filter(Exam.section_id == section_id).first():
        blocking.append("exams")
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: this section has {', '.join(blocking)}. Archive it instead."
        )

    sec_name = getattr(section, "name", "")
    school_id = section.school_id
    section_crud.delete_section(db, section)
    write_audit_log(
        db, user_id=current_user.id, school_id=school_id,
        action="DELETE", resource_type="Section", resource_id=section_id,
        details={"name": sec_name}
    )
    return None