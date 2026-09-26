# backend-python/app/routers/v1/teacher_assignments.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User
from app.models import Timetable
from app.crud.timetable import parse_time
from app.core.audit import write_audit_log

router = APIRouter(prefix="/teacher-assignments", tags=["Teacher Assignments"])


@router.get("", response_model=List[dict])
def list_assignments(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    role = str(current_user.role).upper()
    if role == "STUDENT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if role == "TEACHER":
        from app.crud import teacher as teacher_crud
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher or teacher.id != teacher_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only view your own assignments")
    elif role == "PRINCIPAL":
        from app.models.teacher import Teacher
        teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
        if not teacher or teacher.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher does not belong to your school")
    elif role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    timetables = db.query(Timetable).filter(Timetable.teacher_id == teacher_id).all()
    return [
        {
            "id": t.id,
            "teacher_id": t.teacher_id,
            "section_id": getattr(t, "section_id", None),
            "subject_id": getattr(t, "subject_id", None)
        }
        for t in timetables
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    from app.services.timetable import TimetableService
    from app.schemas.timetable import TimetableCreate
    try:
        obj_in = TimetableCreate(**payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else payload.get("school_id")
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")
    item = TimetableService.create_timetable(db, obj_in=obj_in, school_id=int(school_id))
    write_audit_log(
        db, user_id=current_user.id, school_id=int(school_id),
        action="CREATE", resource_type="TeacherAssignment", resource_id=item["id"], details={}
    )
    return {
        "id": item["id"],
        "teacher_id": item.get("teacher_id"),
        "section_id": item.get("section_id"),
        "subject_id": item.get("subject_id"),
    }


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    from app.services.timetable import TimetableService
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    try:
        TimetableService.delete_timetable(db, timetable_id=assignment_id, school_id=school_id)
        write_audit_log(
            db, user_id=current_user.id, school_id=school_id,
            action="DELETE", resource_type="TeacherAssignment", resource_id=assignment_id, details={}
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found or access denied")
    return None