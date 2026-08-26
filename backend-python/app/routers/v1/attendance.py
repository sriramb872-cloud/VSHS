# backend-python/app/routers/v1/attendance.py
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import attendance as att_crud, student as student_crud
from app.models.user import User
from app.schemas.attendance import AttendanceCreate

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("", response_model=List[dict])
def get_attendance(
    section_id: Optional[int] = None,
    attendance_date: Optional[date] = None,
    student_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    role = str(current_user.role).upper()
    if role == "STUDENT":
        student = student_crud.get_student_by_user_id(db, current_user.id)
        if not student:
            return []
        items = att_crud.get_student_attendance(db, student.id)
    elif student_id:
        student = student_crud.get_student(db, student_id)
        if not student:
            return []
        if role != "SUPER_ADMIN" and student.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        items = att_crud.get_student_attendance(db, student_id)
    elif section_id and attendance_date:
        items = att_crud.get_attendance_by_date(db, section_id, attendance_date)
    elif section_id:
        items = att_crud.get_attendance_by_section(db, section_id, skip, limit)
    else:
        items = []

    return [
        {
            "id": i.id,
            "student_id": i.student_id,
            "section_id": i.section_id,
            "date": str(getattr(i, "date", "")),
            "status": getattr(i, "status", ""),
        }
        for i in items
    ]


@router.get("/student/{student_id}", response_model=dict)
def get_student_attendance_summary(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    student = student_crud.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    role = str(current_user.role).upper()
    if role == "STUDENT":
        if student.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif role != "SUPER_ADMIN" and student.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    records = att_crud.get_student_attendance(db, student_id)
    total_days = len(records)
    present_days = sum(1 for r in records if str(getattr(r, "status", "")).upper() == "PRESENT")
    absent_days = sum(1 for r in records if str(getattr(r, "status", "")).upper() == "ABSENT")
    late_days = sum(1 for r in records if str(getattr(r, "status", "")).upper() == "LATE")
    leave_days = sum(1 for r in records if str(getattr(r, "status", "")).upper() == "LEAVE")
    percentage = round((present_days / total_days * 100), 1) if total_days > 0 else 0.0

    return {
        "student_id": student_id,
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "leave_days": leave_days,
        "percentage": percentage,
        "records": [
            {
                "id": r.id,
                "date": str(r.date),
                "status": str(r.status),
            }
            for r in sorted(records, key=lambda x: x.date, reverse=True)[:30]
        ]
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    data = payload.model_dump()
    if not data.get("recorded_by"):
        data["recorded_by"] = current_user.id
    item = att_crud.create_attendance(db, data)
    return {
        "id": item.id,
        "student_id": item.student_id,
        "section_id": item.section_id,
        "date": str(getattr(item, "date", "")),
        "status": str(getattr(item, "status", ""))
    }


@router.post("/bulk", response_model=List[dict], status_code=status.HTTP_201_CREATED)
def mark_bulk_attendance(
    payload: List[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    results = []
    for entry in payload:
        if "recorded_by" not in entry:
            entry["recorded_by"] = current_user.id
        item = att_crud.create_attendance(db, entry)
        results.append({
            "id": item.id,
            "student_id": item.student_id,
            "section_id": item.section_id,
            "date": str(getattr(item, "date", "")),
            "status": str(getattr(item, "status", ""))
        })
    return results