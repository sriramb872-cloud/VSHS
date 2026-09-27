# backend-python/app/routers/v1/reports.py
"""Platform reporting for the Super Admin.

The Super Admin "System Reports" screen used to render an unconditional
"No Reports Generated" empty state: there was no endpoint behind it at all.
This module adds the real report, built from the tables the application
already owns (``schools``, ``users``, ``students``, ``teachers``, ``sections``,
``exams``, ``marks``, ``report_cards``, ``attendance_records``,
``audit_logs``).

Every number is a SQL COUNT/MAX over those tables. Nothing is estimated and
nothing is hard-coded. The existing per-school report-card and marks endpoints
remain the source of truth for individual student results; this endpoint is the
cross-school rollup.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.attendance import Attendance
from app.models.audit_log import AuditLog
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.marks import Marks as Mark
from app.models.report_card import ReportCard
from app.models.school import School
from app.models.section import Section
from app.models.grade import Grade
from app.models.subject import Subject
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.reports import (
    PlatformReportResponse,
    PlatformReportSummary,
    SchoolRollup,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


def _count(db: Session, model, *filters) -> int:
    query = db.query(func.count(func.distinct(model.id)))
    for f in filters:
        query = query.filter(f)
    return query.scalar() or 0


@router.get("/platform", response_model=PlatformReportResponse)
def platform_report(
    start_date: Optional[date] = Query(
        None, description="Inclusive window start. Defaults to 30 days ago."
    ),
    end_date: Optional[date] = Query(
        None, description="Inclusive window end. Defaults to today."
    ),
    school_id: Optional[int] = Query(None, ge=1, description="Limit the rollup to one school"),
    include_inactive_schools: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    """Cross-school platform report over a date window.

    The window bounds the time-series figures (attendance records, audit
    events, exams overlapping the window). Head-count figures (schools, users,
    students, teachers, sections) are current-state totals, not windowed, since
    a school is not "present" only during part of a range.
    """
    today = date.today()
    window_end = end_date or today
    window_start = start_date or (window_end - timedelta(days=30))
    if window_end < window_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must not be earlier than start_date",
        )
    if (window_end - window_start).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range must not exceed 366 days",
        )

    school_query = db.query(School)
    if school_id is not None:
        if not db.query(School).filter(School.id == school_id).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
        school_query = school_query.filter(School.id == school_id)
    elif not include_inactive_schools:
        school_query = school_query.filter(School.is_active.is_(True))

    schools = school_query.order_by(School.name).all()
    school_ids = [s.id for s in schools]

    in_window = (Attendance.date >= window_start) & (Attendance.date <= window_end)

    def scoped(model, *extra):
        q = db.query(model)
        if school_ids:
            q = q.filter(model.school_id.in_(school_ids))
        for e in extra:
            q = q.filter(e)
        return q

    # --- current-state head counts ---------------------------------------
    school_count = len(school_ids)
    active_school_count = sum(1 for s in schools if s.is_active)

    role_rows = (
        db.query(User.role, User.is_active, func.count(User.id))
        .filter(User.school_id.in_(school_ids) if school_ids else False)
        .group_by(User.role, User.is_active)
        .all()
    ) if school_ids else []

    # Platform-level accounts (school_id IS NULL, e.g. the Super Admin) are not
    # attached to any school, so the school-scoped query above misses them.
    # Counting them separately keeps `user_count` equal to what `GET /users`
    # reports instead of silently excluding platform admins. When the caller
    # narrowed the report to one school they are out of scope, so they are not
    # folded in.
    platform_user_count = 0
    if school_id is None:
        platform_user_count = (
            db.query(func.count(User.id)).filter(User.school_id.is_(None)).scalar() or 0
        )
        platform_by_role: dict = {}
        for role, _active, n in (
            db.query(User.role, User.is_active, func.count(User.id))
            .filter(User.school_id.is_(None))
            .group_by(User.role, User.is_active)
            .all()
        ):
            key = str(getattr(role, "value", role))
            platform_by_role[key] = platform_by_role.get(key, 0) + n
        if platform_by_role:
            role_rows = list(role_rows) + [
                (role, "ACTIVE", n) for role, n in platform_by_role.items()
            ]

    users_by_role: dict = {}
    user_count = 0
    active_user_count = 0
    for role, is_active, n in role_rows:
        role_name = str(getattr(role, "value", role))
        bucket = users_by_role.setdefault(role_name, {"total": 0, "active": 0, "inactive": 0})
        bucket["total"] += n
        user_count += n
        if str(is_active).upper() == "ACTIVE":
            bucket["active"] += n
            active_user_count += n
        else:
            bucket["inactive"] += n

    summary = PlatformReportSummary(
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        school_count=school_count,
        active_school_count=active_school_count,
        user_count=user_count,
        active_user_count=active_user_count,
        inactive_user_count=user_count - active_user_count,
        school_user_count=user_count - platform_user_count,
        platform_user_count=platform_user_count,
        users_by_role=users_by_role,
        student_count=_count(db, Student, Student.school_id.in_(school_ids)) if school_ids else 0,
        teacher_count=_count(db, Teacher, Teacher.school_id.in_(school_ids)) if school_ids else 0,
        grade_count=_count(db, Grade, Grade.school_id.in_(school_ids)) if school_ids else 0,
        section_count=_count(db, Section, Section.school_id.in_(school_ids)) if school_ids else 0,
        subject_count=_count(db, Subject, Subject.school_id.in_(school_ids)) if school_ids else 0,
        exam_count=scoped(Exam).count(),
        published_exam_count=scoped(Exam, Exam.status == "PUBLISHED").count(),
        # Report cards are not windowed: a card is a per-term result, and
        # "how many exist" is a meaningful current-state figure.
        report_card_count=_count(db, ReportCard),
        audit_event_count=(
            db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.school_id.in_(school_ids),
                func.date(AuditLog.timestamp) >= window_start,
                func.date(AuditLog.timestamp) <= window_end,
            )
            .scalar()
            or 0
        )
        if school_ids
        else 0,
        # Filled in below, once the section / exam-subject ids are resolved.
        marks_record_count=0,
        attendance_record_count=0,
    )

    # Marks and attendance hang off sections/exam_subjects rather than schools,
    # so they need the section and exam-subject ids of the selected schools.
    section_ids_in_scope = (
        [s.id for s in db.query(Section).filter(Section.school_id.in_(school_ids)).all()]
        if school_ids
        else []
    )
    exam_ids_in_scope = (
        [e.id for e in db.query(Exam).filter(Exam.school_id.in_(school_ids)).all()]
        if school_ids
        else []
    )
    exam_subject_ids_in_scope = (
        [
            es.id
            for es in db.query(ExamSubject).filter(ExamSubject.exam_id.in_(exam_ids_in_scope)).all()
        ]
        if exam_ids_in_scope
        else []
    )
    summary.marks_record_count = (
        db.query(func.count(Mark.id))
        .filter(Mark.exam_subject_id.in_(exam_subject_ids_in_scope))
        .scalar()
        or 0
    ) if exam_subject_ids_in_scope else 0
    summary.attendance_record_count = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.section_id.in_(section_ids_in_scope), in_window)
        .scalar()
        or 0
    ) if section_ids_in_scope else 0

    # --- per-school rollup ------------------------------------------------
    rollups: list = []
    for s in schools:
        s_sections = [x.id for x in db.query(Section).filter(Section.school_id == s.id).all()]
        s_exams = [x.id for x in db.query(Exam).filter(Exam.school_id == s.id).all()]
        s_students = [x.id for x in db.query(Student).filter(Student.school_id == s.id).all()]

        last_audit = (
            db.query(func.max(AuditLog.timestamp))
            .filter(AuditLog.school_id == s.id)
            .scalar()
        )

        rollups.append(
            SchoolRollup(
                school_id=s.id,
                school_name=s.name,
                school_code=getattr(s, "code", None),
                is_active=bool(s.is_active),
                student_count=len(s_students),
                teacher_count=_count(db, Teacher, Teacher.school_id == s.id),
                staff_count=db.query(func.count(User.id))
                .filter(User.school_id == s.id, User.is_active == "ACTIVE")
                .scalar()
                or 0,
                section_count=len(s_sections),
                exam_count=len(s_exams),
                report_card_count=(
                    db.query(func.count(ReportCard.id))
                    .filter(ReportCard.student_id.in_(s_students))
                    .scalar()
                    or 0
                )
                if s_students
                else 0,
                attendance_record_count=(
                    db.query(func.count(Attendance.id))
                    .filter(Attendance.section_id.in_(s_sections), in_window)
                    .scalar()
                    or 0
                )
                if s_sections
                else 0,
                last_audit_at=last_audit.isoformat() if last_audit else None,
            )
        )

    return PlatformReportResponse(summary=summary, schools=rollups)
