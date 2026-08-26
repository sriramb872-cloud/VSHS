# backend-python/app/routers/v1/teacher_assignments.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User
from app.models import Timetable
from app.crud.timetable import parse_time

router = APIRouter(prefix="/teacher-assignments", tags=["Teacher Assignments"])


@router.get("", response_model=List[dict])
def list_assignments(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
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
    data = dict(payload)
    if "start_time" in data and data["start_time"] is not None:
        data["start_time"] = parse_time(data["start_time"])
    if "end_time" in data and data["end_time"] is not None:
        data["end_time"] = parse_time(data["end_time"])
    item = Timetable(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "teacher_id": item.teacher_id,
        "section_id": getattr(item, "section_id", None),
        "subject_id": getattr(item, "subject_id", None)
    }


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    item = db.query(Timetable).filter(Timetable.id == assignment_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(item)
    db.commit()
    return None