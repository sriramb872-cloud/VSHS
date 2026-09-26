# backend-python/app/routers/v1/attendance.py
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import attendance as att_crud, student as student_crud, teacher as teacher_crud
from app.models.section import Section
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.schemas.attendance import AttendanceCreate
from app.core.audit import write_audit_log

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _assert_teacher_owns_section(db: Session, current_user: User, section_id: Optional[int]):
    if str(current_user.role).upper() != "TEACHER":
        return
    if not section_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section ID is required"
        )
    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section or section.school_id != teacher.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Section not found or does not belong to your school"
        )
    is_class_teacher = (section.class_teacher_id == teacher.id)
    is_subject_teacher = (
        db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == teacher.id,
            TeacherSubject.section_id == section_id
        ).first() is not None
    )
    if not (is_class_teacher or is_subject_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher is neither class teacher nor assigned subject teacher for this section"
        )


def _assert_teacher_can_view_student(db: Session, current_user: User, student) -> None:
    if str(current_user.role).upper() != "TEACHER":
        return
    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    from app.models.student_enrollment import StudentEnrollment
    enrollment = (
        db.query(StudentEnrollment)
        .filter(StudentEnrollment.student_id == student.id)
        .order_by(StudentEnrollment.created_at.desc(), StudentEnrollment.id.desc())
        .first()
    )
    if not enrollment or not enrollment.section_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    _assert_teacher_owns_section(db, current_user, enrollment.section_id)


def _assert_section_access(db: Session, current_user: User, section_id: int):
    role = str(current_user.role).upper()
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if role == "SUPER_ADMIN":
        return
    if role == "PRINCIPAL":
        if section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, section_id)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _assert_attendance_write_allowed(db: Session, current_user: User, section_id: Optional[int], student_id: Optional[int] = None):
    role = str(current_user.role).upper()
    if not section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section ID is required")
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    if role == "SUPER_ADMIN":
        pass  # cross-school allowed, but still validate relationship below
    elif role == "PRINCIPAL":
        if section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section does not belong to your school")
    elif role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, section_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if student_id:
        student = student_crud.get_student(db, student_id)
        if not student or student.school_id != section.school_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student does not belong to this section's school")
        # also confirm active enrollment in this section
        from app.models.student_enrollment import StudentEnrollment
        enrolled = db.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == student_id,
            StudentEnrollment.section_id == section_id,
        ).first()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not enrolled in this section")


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
        if role == "TEACHER":
            _assert_teacher_can_view_student(db, current_user, student)
        elif role != "SUPER_ADMIN" and student.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        items = att_crud.get_student_attendance(db, student_id)
    elif section_id and attendance_date:
        _assert_section_access(db, current_user, section_id)
        items = att_crud.get_attendance_by_date(db, section_id, attendance_date)
    elif section_id:
        _assert_section_access(db, current_user, section_id)
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
            "remarks": getattr(i, "remarks", None),
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
    elif role == "TEACHER":
        _assert_teacher_can_view_student(db, current_user, student)
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
    _assert_attendance_write_allowed(db, current_user, payload.section_id, payload.student_id)
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
    for entry in payload:
        sid = entry.get("section_id") if isinstance(entry, dict) else getattr(entry, "section_id", None)
        stid = entry.get("student_id") if isinstance(entry, dict) else getattr(entry, "student_id", None)
        _assert_attendance_write_allowed(db, current_user, sid, stid)

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

@router.patch("/{attendance_id}", response_model=dict)
def correct_attendance(
    attendance_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    """Correct/update an attendance record. Prefer correction over deletion."""
    item = att_crud.get_attendance(db, attendance_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    role = str(current_user.role).upper()
    if role != "SUPER_ADMIN" and getattr(item, "school_id", None) and getattr(item, "school_id") != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, item.section_id)

    old_status = getattr(item, "status", None)
    allowed = {"status", "remarks"}
    for k, v in payload.items():
        if k in allowed and v is not None:
            setattr(item, k, v)
    db.commit()
    db.refresh(item)

    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="CORRECTION", resource_type="Attendance", resource_id=attendance_id,
        details={"old_status": str(old_status), "new_status": payload.get("status")},
    )
    return {
        "id": item.id,
        "student_id": item.student_id,
        "section_id": item.section_id,
        "date": str(getattr(item, "date", "")),
        "status": str(getattr(item, "status", "")),
    }


@router.post("/{attendance_id}/void", response_model=dict)
def void_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    item = att_crud.get_attendance(db, attendance_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
    role = str(current_user.role).upper()
    if role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, item.section_id)
    elif role == "PRINCIPAL":
        section = db.query(Section).filter(Section.id == item.section_id).first()
        if not section or section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    old_status = item.status
    item.status = "VOID"
    db.commit()
    db.refresh(item)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="VOID", resource_type="Attendance", resource_id=attendance_id,
        details={"old_status": str(old_status)},
    )
    return {
        "id": item.id,
        "student_id": item.student_id,
        "section_id": item.section_id,
        "date": str(item.date),
        "status": str(item.status),
    }
