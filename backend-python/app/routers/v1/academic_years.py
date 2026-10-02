# backend-python/app/routers/v1/academic_years.py
"""Academic year lifecycle API.

Statuses: UPCOMING -> ACTIVE -> CLOSED -> ARCHIVED.

* at most one ACTIVE year per school;
* activating a year atomically closes the previously active one;
* ACTIVE years cannot be deleted, years that contain data must be archived;
* ARCHIVED years are read-only.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.api.year_context import resolve_academic_year, get_school_active_year
from app.crud import academic_year as ay_crud
from app.crud.academic_year import (
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    STATUS_CLOSED,
    STATUS_UPCOMING,
)
from app.models.user import User
from app.models.academic_year import AcademicYear
from app.models.announcement import Announcement
from app.models.attendance import Attendance
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.homework import Homework
from app.models.marks import Marks
from app.models.report_card import ReportCard
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher_subject import TeacherSubject
from app.models.timetable import Timetable
from app.core.audit import write_audit_log
from app.schemas.academic_year import AcademicYearCreate, AcademicYearUpdate

router = APIRouter(prefix="/academic-years", tags=["Academic Years"])


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _serialize(year: AcademicYear) -> dict:
    return {
        "id": year.id,
        "school_id": year.school_id,
        "name": getattr(year, "name", ""),
        "status": getattr(year, "status", None) or STATUS_UPCOMING,
        "is_active": bool(getattr(year, "is_active", False))
        or (getattr(year, "status", None) == STATUS_ACTIVE),
        "start_date": str(getattr(year, "start_date", "") or ""),
        "end_date": str(getattr(year, "end_date", "") or ""),
        "created_at": str(getattr(year, "created_at", "") or ""),
    }


def _assert_manageable(year: AcademicYear, current_user: User) -> None:
    role = str(current_user.role).upper()
    if role == "SUPER_ADMIN":
        return
    if year.school_id != current_user.school_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")


def _assert_school(current_user: User, payload_school_id: Optional[int] = None) -> int:
    role = str(current_user.role).upper()
    if current_user.school_id:
        return current_user.school_id
    if role == "SUPER_ADMIN" and payload_school_id:
        return payload_school_id
    raise HTTPException(
        status_code=http_status.HTTP_400_BAD_REQUEST, detail="School ID is required"
    )


def _check_overlap(db: Session, start_date, end_date, school_id: int, exclude_id: Optional[int] = None) -> None:
    if not start_date or not end_date:
        return
    if start_date >= end_date:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )
    overlap = ay_crud.find_overlapping_year(
        db, school_id, start_date, end_date, exclude_id=exclude_id
    )
    if overlap is not None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                "Academic year overlaps with existing year "
                f"'{getattr(overlap, 'name', '')}' "
                f"({overlap.start_date} to {overlap.end_date})"
            ),
        )


def _year_has_data(db: Session, year: AcademicYear) -> List[str]:
    """Names of data kinds that make a year unsafe to delete."""
    year_id = year.id
    blocking: List[str] = []

    def _count(model, *criterion):
        try:
            return db.query(func.count(model.id)).filter(*criterion).scalar() or 0
        except Exception:  # noqa: BLE001 - never let a model quirk block a reply
            return 0

    if _count(StudentEnrollment, StudentEnrollment.academic_year_id == year_id):
        blocking.append("student enrollments")
    if _count(Exam, Exam.academic_year_id == year_id):
        blocking.append("exams")
    if _count(Timetable, Timetable.academic_year_id == year_id):
        blocking.append("timetable entries")
    if _count(
        Marks,
        Marks.exam_subject.has(ExamSubject.exam.has(Exam.academic_year_id == year_id)),
    ):
        blocking.append("recorded marks")
    if _count(ReportCard, ReportCard.academic_year_id == year_id):
        blocking.append("report cards")
    if _count(Homework, Homework.academic_year_id == year_id):
        blocking.append("homework")
    if _count(Announcement, Announcement.academic_year_id == year_id):
        blocking.append("announcements")
    if _count(TeacherSubject, TeacherSubject.academic_year_id == year_id):
        blocking.append("teacher assignments")
    if _count(Attendance, Attendance.academic_year_id == year_id):
        blocking.append("attendance records")
    return blocking


def _sync_settings_name(db: Session, school_id: int, year_name: str) -> None:
    """Keep the legacy free-text setting in agreement with the ACTIVE year."""
    from app.models.app_settings import SchoolSettings

    try:
        row = (
            db.query(SchoolSettings)
            .filter(SchoolSettings.school_id == school_id)
            .first()
        )
        if row is not None and (row.academic_year or "") != (year_name or ""):
            row.academic_year = year_name
            db.flush()
    except Exception:  # noqa: BLE001 - never block an activation on a nicety
        db.rollback()


# --------------------------------------------------------------------------
# read endpoints
# --------------------------------------------------------------------------


@router.get("", response_model=List[dict])
def list_academic_years(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    school_id = current_user.school_id
    if not school_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="School context missing"
        )

    years = ay_crud.get_academic_years_by_school(
        db, school_id=school_id, skip=skip, limit=limit
    )
    return [_serialize(y) for y in years]


@router.get("/active", response_model=dict)
def get_active_academic_year_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    request: Request = None,
):
    """The school's ACTIVE year, or a best-effort fallback.

    Honouring the ``X-Academic-Year-Id`` header here lets the frontend ask
    "which year am I looking at?" and get the selected one back.
    """
    try:
        year = resolve_academic_year(db, current_user, request)
    except HTTPException:
        year = None
    if year is None and current_user.school_id:
        year = get_school_active_year(db, current_user.school_id)
    if year is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No academic year configured for this school",
        )
    return _serialize(year)


@router.get("/{academic_year_id}", response_model=dict)
def get_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Academic year not found"
        )

    _assert_manageable(item, current_user)
    return _serialize(item)


# --------------------------------------------------------------------------
# write endpoints
# --------------------------------------------------------------------------


@router.post("", response_model=dict, status_code=http_status.HTTP_201_CREATED)
def create_academic_year(
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    school_id = _assert_school(current_user, payload.school_id)

    name = payload.name
    if name and ay_crud.get_academic_year_by_name(db, school_id, name):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Academic year name already exists",
        )

    _check_overlap(db, payload.start_date, payload.end_date, school_id)

    data = payload.model_dump()
    wants_active = bool(data.pop("is_active", False))
    data["status"] = STATUS_UPCOMING
    data["is_active"] = False

    item = ay_crud.create_academic_year(db, school_id, data)

    if wants_active:
        item = _activate(db, item, current_user)

    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=school_id,
        action="CREATE",
        resource_type="AcademicYear",
        resource_id=item.id,
        details={"name": item.name, "status": item.status},
    )
    return _serialize(item)


@router.patch("/{academic_year_id}", response_model=dict)
def update_academic_year(
    academic_year_id: int,
    payload: AcademicYearUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Academic year not found"
        )

    _assert_manageable(item, current_user)

    if item.status == STATUS_ARCHIVED:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Archived academic years cannot be edited",
        )

    data = payload.model_dump(exclude_unset=True)
    data.pop("is_active", None)
    if not data:
        return _serialize(item)

    new_start = data.get("start_date", item.start_date)
    new_end = data.get("end_date", item.end_date)
    if "name" in data and data["name"] != item.name:
        existing = ay_crud.get_academic_year_by_name(db, item.school_id, data["name"])
        if existing is not None and existing.id != item.id:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Academic year name already exists",
            )
    _check_overlap(db, new_start, new_end, item.school_id, exclude_id=item.id)

    updated = ay_crud.update_academic_year(db, item, data)
    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=item.school_id,
        action="UPDATE",
        resource_type="AcademicYear",
        resource_id=item.id,
        details={k: str(v) for k, v in data.items()},
    )
    return _serialize(updated)


def _activate(db: Session, item: AcademicYear, current_user: User) -> AcademicYear:
    """Atomically make ``item`` the single ACTIVE year of its school."""
    previous = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.school_id == item.school_id,
            AcademicYear.id != item.id,
            AcademicYear.status == STATUS_ACTIVE,
        )
        .all()
    )
    ay_crud.deactivate_other_years(db, item.school_id, item.id)
    for other in previous:
        other.status = STATUS_CLOSED
    item.status = STATUS_ACTIVE
    item.is_active = True
    db.flush()
    db.refresh(item)
    _sync_settings_name(db, item.school_id, item.name)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{academic_year_id}/activate", response_model=dict)
def activate_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Academic year not found"
        )
    _assert_manageable(item, current_user)

    if item.status == STATUS_ARCHIVED:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Archived academic years cannot be activated",
        )
    if item.status == STATUS_ACTIVE:
        return _serialize(item)

    item = _activate(db, item, current_user)
    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=item.school_id,
        action="ACTIVATE",
        resource_type="AcademicYear",
        resource_id=item.id,
        details={"name": item.name},
    )
    return _serialize(item)


@router.post("/{academic_year_id}/archive", response_model=dict)
def archive_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Academic year not found"
        )
    _assert_manageable(item, current_user)

    if item.status == STATUS_ARCHIVED:
        return _serialize(item)

    was_active = item.status == STATUS_ACTIVE or item.is_active
    item.status = STATUS_ARCHIVED
    item.is_active = False
    db.flush()

    if was_active:
        # Keep the school usable: fall back to the most recent non-archived
        # year so requests without an explicit year still resolve.
        fallback = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.school_id == item.school_id,
                AcademicYear.id != item.id,
                AcademicYear.status != STATUS_ARCHIVED,
            )
            .order_by(AcademicYear.start_date.desc())
            .first()
        )
        if fallback is not None:
            today = date.today()
            fallback.status = (
                STATUS_ACTIVE
                if fallback.start_date <= today <= fallback.end_date
                else STATUS_CLOSED
                if fallback.end_date < today
                else STATUS_UPCOMING
            )
            fallback.is_active = fallback.status == STATUS_ACTIVE
            db.flush()
            if fallback.is_active:
                _sync_settings_name(db, item.school_id, fallback.name)

    db.commit()
    db.refresh(item)
    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=item.school_id,
        action="ARCHIVE",
        resource_type="AcademicYear",
        resource_id=item.id,
        details={"name": item.name},
    )
    return _serialize(item)


@router.delete("/{academic_year_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    item = ay_crud.get_academic_year(db, academic_year_id)
    if not item:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Academic year not found"
        )

    _assert_manageable(item, current_user)

    if item.status == STATUS_ACTIVE or item.is_active:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the currently active academic year.",
        )

    blocking = _year_has_data(db, item)
    if blocking:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete: this academic year has {', '.join(blocking)}. "
                "Archive it instead."
            ),
        )

    ay_name = getattr(item, "name", "")
    school_id = item.school_id
    ay_crud.delete_academic_year(db, item)
    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=school_id,
        action="DELETE",
        resource_type="AcademicYear",
        resource_id=academic_year_id,
        details={"name": ay_name},
    )
    return None
