# backend-python/app/routers/v1/attendance.py
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import attendance as att_crud, student as student_crud, teacher as teacher_crud
from app.models.attendance import Attendance
from app.models.section import Section
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.models.attendance_record import AttendanceStatus
from app.schemas.attendance import AttendanceCreate
from app.serializers.attendance import serialize_attendance_record
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

    return [serialize_attendance_record(i) for i in items]


# ---------------------------------------------------------------------------
# Attendance reporting
# ---------------------------------------------------------------------------

_REPORT_STATUSES = ("PRESENT", "ABSENT", "LATE", "LEAVE", "VOID")


def _rate(present: int, marked: int) -> float:
    """Attendance rate = present / (marked, excluding VOID).

    VOID rows are corrections that must not count towards attendance, so they
    are excluded from the denominator.
    """
    return round((present / marked) * 100, 1) if marked else 0.0


def _teacher_section_ids(db: Session, current_user: User) -> List[int]:
    """Sections a teacher may see: class-teacher sections plus subject assignments."""
    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
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


@router.get("/reports/summary", response_model=dict)
def attendance_report_summary(
    start_date: date = Query(..., description="First day of the report window (inclusive)"),
    end_date: date = Query(..., description="Last day of the report window (inclusive)"),
    grade_id: Optional[int] = Query(None, ge=1),
    section_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"])),
):
    """Aggregated attendance over a date range, scoped to the caller's tenant.

    Every number below is a COUNT over `attendance_records`; nothing is
    estimated. `attendance_rate` is present / marked where marked excludes VOID.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must not be earlier than start_date",
        )
    if (end_date - start_date).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range must not exceed 366 days",
        )

    role = str(current_user.role).upper()

    # --- resolve the set of sections the caller may report on -------------
    section_query = db.query(Section)
    if role == "SUPER_ADMIN":
        pass  # platform-wide
    elif role == "PRINCIPAL":
        if not current_user.school_id:
            return {
                "filters": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "grade_id": grade_id,
                    "section_id": section_id,
                },
                "totals": {s: 0 for s in _REPORT_STATUSES}
                | {"marked": 0, "students": 0, "attendance_rate": 0.0},
                "daily": [],
                "sections": [],
                "students": [],
            }
        section_query = section_query.filter(Section.school_id == current_user.school_id)
    else:  # TEACHER
        allowed = _teacher_section_ids(db, current_user)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to any section, so there is no attendance to report.",
            )
        section_query = section_query.filter(Section.id.in_(allowed))

    if grade_id is not None:
        section_query = section_query.filter(Section.grade_id == grade_id)
    if section_id is not None:
        section_query = section_query.filter(Section.id == section_id)

    sections = section_query.all()
    if section_id is not None and not sections:
        # Distinguish "no access" from "does not exist" without leaking
        # anything about other tenants' sections.
        if role != "SUPER_ADMIN":
            _assert_section_access(db, current_user, section_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    section_ids = [s.id for s in sections]
    section_by_id = {s.id: s for s in sections}
    grade_ids = {s.grade_id for s in sections}

    from app.models.grade import Grade

    grade_name_by_id = {
        g.id: g.name for g in db.query(Grade).filter(Grade.id.in_(grade_ids)).all()
    } if grade_ids else {}

    if not section_ids:
        return {
            "filters": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "grade_id": grade_id,
                "section_id": section_id,
            },
            "totals": {s: 0 for s in _REPORT_STATUSES}
            | {"marked": 0, "students": 0, "attendance_rate": 0.0},
            "daily": [],
            "sections": [],
            "students": [],
        }

    rows = (
        db.query(
            Attendance.date,
            Attendance.section_id,
            Attendance.status,
            func.count(Attendance.id),
        )
        .filter(
            Attendance.section_id.in_(section_ids),
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        )
        .group_by(Attendance.date, Attendance.section_id, Attendance.status)
        .all()
    )

    def blank() -> dict:
        return {s: 0 for s in _REPORT_STATUSES}

    totals = blank()
    per_section: dict = {sid: blank() for sid in section_ids}
    per_day: dict = {}

    for day, sid, st, count in rows:
        # NB: must not be named `status` - that would shadow the imported
        # `fastapi.status` module for the whole function and turn every
        # `status.HTTP_*` reference in here into an UnboundLocalError.
        row_status = (getattr(st, "value", None) or str(st)).upper()
        if row_status not in totals:
            continue
        totals[row_status] += count
        per_section[sid][row_status] += count
        per_day.setdefault(day.isoformat(), blank())[row_status] += count

    # Per-student totals need a second pass because the grouped query above is
    # keyed by section/day, not by student.
    student_rows = (
        db.query(
            Attendance.student_id,
            Attendance.section_id,
            Attendance.status,
            func.count(Attendance.id),
        )
        .filter(
            Attendance.section_id.in_(section_ids),
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        )
        .group_by(Attendance.student_id, Attendance.section_id, Attendance.status)
        .all()
    )
    per_student: dict = {}
    for student_id, sid, st, count in student_rows:
        row_status = (getattr(st, "value", None) or str(st)).upper()
        if row_status not in totals:
            continue
        key = (student_id, sid)
        per_student.setdefault(key, blank())[row_status] += count

    total_marked = sum(totals[s] for s in _REPORT_STATUSES if s != "VOID")

    def section_row(sid: int) -> dict:
        counts = per_section[sid]
        marked = sum(counts[s] for s in _REPORT_STATUSES if s != "VOID")
        sec = section_by_id[sid]
        return {
            "section_id": sid,
            "grade_id": sec.grade_id,
            "grade_name": grade_name_by_id.get(sec.grade_id),
            "section_name": sec.name,
            "marked": marked,
            "attendance_rate": _rate(counts["PRESENT"], marked),
            **counts,
        }

    from app.models.student import Student
    from app.models.student_enrollment import StudentEnrollment

    enrolled_rows = (
        db.query(StudentEnrollment.section_id, func.count(func.distinct(StudentEnrollment.student_id)))
        .filter(StudentEnrollment.section_id.in_(section_ids))
        .group_by(StudentEnrollment.section_id)
        .all()
    )
    enrolled_by_section = {sid: n for sid, n in enrolled_rows}

    # Distinct students that actually have at least one record in this section.
    students_with_records_by_section: dict = {}
    for (_student_id, sid) in per_student:
        students_with_records_by_section[sid] = students_with_records_by_section.get(sid, 0) + 1

    section_rows = []
    for sid in section_ids:
        row = section_row(sid)
        row["enrolled_students"] = enrolled_by_section.get(sid, 0)
        row["students_with_records"] = students_with_records_by_section.get(sid, 0)
        section_rows.append(row)

    # per-student detail
    student_ids = sorted({s for s, _sec in per_student})
    student_by_id = {}
    if student_ids:
        student_by_id = {
            s.id: s
            for s in db.query(Student).filter(Student.id.in_(student_ids)).all()
        }
    from app.models.user import User as _User

    name_by_user = {}
    if student_by_id:
        user_ids = [s.user_id for s in student_by_id.values() if s.user_id]
        if user_ids:
            name_by_user = {
                u.id: (getattr(u, "display_name", None) or u.mobile)
                for u in db.query(_User).filter(_User.id.in_(user_ids)).all()
            }

    student_rows_out = []
    for (student_id, sid), counts in sorted(per_student.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        marked = sum(counts[s] for s in _REPORT_STATUSES if s != "VOID")
        stu = student_by_id.get(student_id)
        sec = section_by_id.get(sid)
        student_rows_out.append({
            "student_id": student_id,
            "student_name": name_by_user.get(stu.user_id) if stu else None,
            "admission_number": stu.admission_number if stu else None,
            "roll_number": stu.roll_number if stu else None,
            "section_id": sid,
            "grade_name": grade_name_by_id.get(sec.grade_id) if sec else None,
            "section_name": sec.name if sec else None,
            "marked": marked,
            "attendance_rate": _rate(counts["PRESENT"], marked),
            **counts,
        })

    daily_rows = []
    for day_key in sorted(per_day):
        counts = per_day[day_key]
        marked = sum(counts[s] for s in _REPORT_STATUSES if s != "VOID")
        daily_rows.append({
            "date": day_key,
            "marked": marked,
            "attendance_rate": _rate(counts["PRESENT"], marked),
            **counts,
        })

    return {
        "filters": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "grade_id": grade_id,
            "section_id": section_id,
        },
        "totals": {
            **totals,
            "marked": total_marked,
            "students": len(student_ids),
            "attendance_rate": _rate(totals["PRESENT"], total_marked),
        },
        "daily": daily_rows,
        "sections": section_rows,
        "students": student_rows_out,
    }


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
    return serialize_attendance_record(item)


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
        # Validate the status up front. This endpoint takes raw dicts, so an
        # unknown status used to reach MySQL and fail as a 500.
        raw_status = entry.get("status") if isinstance(entry, dict) else getattr(entry, "status", None)
        try:
            AttendanceStatus(str(getattr(raw_status, "value", raw_status)).upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid attendance status: {raw_status!r}",
            )

    results = []
    for entry in payload:
        if "recorded_by" not in entry:
            entry["recorded_by"] = current_user.id
        item = att_crud.create_attendance(db, entry)
        results.append(serialize_attendance_record(item))
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
    # The Attendance model has no school_id column, so the section is the only
    # way to resolve ownership. Previously this branch tested
    # `getattr(item, "school_id", None)`, which is always None on this model,
    # making the whole condition False and leaving PRINCIPAL with no ownership
    # check at all - a principal could correct any other school's attendance.
    if role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, item.section_id)
    elif role == "PRINCIPAL":
        section = db.query(Section).filter(Section.id == item.section_id).first()
        if not section or section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    old_status = getattr(item, "status", None)
    allowed = {"status", "remarks"}
    for k, v in payload.items():
        if k in allowed and v is not None:
            if k == "status":
                # This endpoint takes a raw dict, so an unknown status used to
                # reach MySQL and fail as a 500.
                try:
                    AttendanceStatus(str(getattr(v, "value", v)).upper())
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid attendance status: {v!r}",
                    )
            setattr(item, k, v)
    db.commit()
    db.refresh(item)

    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="CORRECTION", resource_type="Attendance", resource_id=attendance_id,
        details={"old_status": str(old_status), "new_status": payload.get("status")},
    )
    return serialize_attendance_record(item)


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
    return serialize_attendance_record(item)
