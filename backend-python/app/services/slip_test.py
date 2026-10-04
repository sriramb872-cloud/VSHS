# backend-python/app/services/slip_test.py
"""Slip test service — authorization, validation and notification fan-out.

Everything security-relevant lives here, never in the router and never in the
frontend:

* **Teacher** may only act on class + subject combinations they are actually
  assigned to as subject teacher, and may only edit/cancel tests they created.
* **Student** is read-only and only ever sees tests for the section they are
  enrolled in *for the resolved academic year*.
* **Every** query is filtered by ``school_id``.

Teacher → class + subject: the existing single source of truth
--------------------------------------------------------------
This module reuses the assignment model the rest of the teacher portal already
uses — the union of two legitimate sources, exactly as
``app/routers/v1/homework.py::_teacher_has_assignment`` defines it:

1. ``timetables`` rows — what the Principal *Timetable* page writes and what
   ``GET /teachers/me`` returns as ``teaching_assignments``;
2. ``teacher_subjects`` rows — what the Principal *Teaching Assignments* page
   writes (a ``NULL academic_year_id`` means "all years", per that model's own
   comment).

No parallel assignment table is introduced. The year filter is deliberately not
applied here either, matching homework: the teacher portal's own class picker
is unfiltered, and a slip-test form that offered fewer classes than the homework
form right next to it would be a support ticket, not a security win. The slip
test itself is still hard-scoped to the active academic year.

Transactions
------------
``create``, ``update`` and ``cancel`` each write the slip test row *and* every
notification in one transaction: ``add`` → ``flush`` → ``add`` → a single
``commit()``. Any failure (including a validation error raised mid-flight) hits
``rollback()``, so a half-written fan-out is impossible. This is why these
methods bypass ``crud_notification.create`` — that helper commits internally,
which would end the transaction after the slip test and before the notices.
"""
import re
from datetime import date, datetime, time as dt_time, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.crud.slip_test import crud_slip_test
from app.models.academic_year import AcademicYear
from app.models.grade import Grade
from app.models.notification import Notification
from app.models.section import Section
from app.models.slip_test import DEFAULT_SLIP_TEST_STATUS, SLIP_TEST_STATUSES, SlipTest
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.timetable import Timetable
from app.models.user import User
from app.repositories.slip_test import SlipTestRepository
from app.schemas.slip_test import (
    MAX_DESCRIPTION_LENGTH,
    SlipTestClassCard,
    SlipTestCreate,
    SlipTestResponse,
    SlipTestUpdate,
)

# ---------------------------------------------------------------------------
# Notification contract
# ---------------------------------------------------------------------------

#: Dedicated notification type + category. A distinct value is what makes the
#: deep link unambiguous: ``reference_id`` is only ever a ``slip_tests.id`` on a
#: row tagged with this category, so the frontend never has to guess what an id
#: refers to.
SLIP_TEST_NOTIFICATION_TYPE = "SLIP_TEST"
SLIP_TEST_NOTIFICATION_CATEGORY = "SLIP_TEST"


# ---------------------------------------------------------------------------
# Text sanitisation
# ---------------------------------------------------------------------------

# Anything that looks like a tag, e.g. `<script>`, `<img src=x onerror=...>`.
_TAG_RE = re.compile(r"<[^>]*>")
# C0/C1 control characters except tab/newline: invisible, and a classic way of
# spoofing a rendered title.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """Strip markup and control characters from free text.

    Defence in depth only: the frontend renders these fields through React, which
    escapes by default (no ``dangerouslySetInnerHTML`` anywhere in this feature),
    so stored HTML could never execute. This removes it at the boundary anyway
    so the database never becomes a store of injected markup that some future
    export (CSV/PDF/email) could render unescaped.
    """
    if value is None:
        return None
    text = _CONTROL_RE.sub("", str(value))
    text = _TAG_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if max_length is not None and len(text) > max_length:
        text = text[:max_length].rstrip()
    return text or None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_date(value: date) -> str:
    """Human-readable school-local date for notification text.

    Formatted from the date parts, never through ``strftime`` on a UTC-shifted
    datetime — a slip test date is a calendar day at the school, not an instant.
    """
    months = (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    )
    return f"{value.day:02d} {months[value.month - 1]} {value.year}"


def _format_time(value) -> Optional[str]:
    if value is None:
        return None
    return value.strftime("%I:%M %p").lstrip("0")


def _when_label(row: SlipTest) -> str:
    """`02 Nov 2026 at 09:30 AM` (time omitted when not set)."""
    label = _format_date(row.scheduled_date)
    time_label = _format_time(row.start_time)
    return f"{label} at {time_label}" if time_label else label


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SlipTestService:
    # -- lookups & shared validation ----------------------------------------

    @staticmethod
    def get_teacher_for_user(db: Session, user: User) -> Teacher:
        teacher = getattr(user, "teacher_profile", None) or (
            db.query(Teacher).filter(Teacher.user_id == user.id).first()
        )
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher profile not found for this user",
            )
        return teacher

    @staticmethod
    def get_student_for_user(db: Session, user: User) -> Student:
        student = getattr(user, "student_profile", None) or (
            db.query(Student).filter(Student.user_id == user.id).first()
        )
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student profile not found for this user",
            )
        return student

    @staticmethod
    def require_open_academic_year(db: Session, academic_year_id: Optional[int]) -> AcademicYear:
        """The year a slip test may be written into must exist and be ACTIVE.

        A CLOSED/ARCHIVED year is history: the portal already renders it
        read-only, and writing into it would let a teacher fabricate a result for
        a term that has ended. UPCOMING is rejected too — the slip test's date
        must sit inside the year, and a year that has not started has no
        "today".
        """
        if academic_year_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An academic year is required to schedule a slip test",
            )
        year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        if not year:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found"
            )
        if str(year.status or "").upper() != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Slip tests can only be scheduled in an active academic year "
                    f"(this year is {year.status})"
                ),
            )
        return year

    @staticmethod
    def _targets_in_school(
        db: Session,
        *,
        school_id: int,
        grade_id: int,
        section_id: int,
        subject_id: int,
    ) -> bool:
        """Grade, section and subject all belong to ``school_id``, and the
        section actually belongs to the grade.

        Checked on every create/update so a foreign object id can never be
        persisted as a cross-tenant reference.
        """
        grade = (
            db.query(Grade)
            .filter(Grade.id == grade_id, Grade.school_id == school_id)
            .first()
        )
        section = (
            db.query(Section)
            .filter(
                Section.id == section_id,
                Section.school_id == school_id,
                Section.grade_id == grade_id,
            )
            .first()
        )
        subject = (
            db.query(Subject)
            .filter(Subject.id == subject_id, Subject.school_id == school_id)
            .first()
        )
        return bool(grade and section and subject)

    @staticmethod
    def teacher_assignments(db: Session, teacher: Teacher, school_id: int) -> Set[Tuple[int, int, int]]:
        """``{(grade_id, section_id, subject_id)}`` this teacher teaches.

        Union of timetable rows and explicit ``teacher_subjects`` rows, both
        school-scoped. See the module docstring for why this mirrors homework.
        """
        if not teacher.school_id or teacher.school_id != school_id:
            return set()

        slots: Set[Tuple[int, int, int]] = set()

        for row in (
            db.query(Timetable.grade_id, Timetable.section_id, Timetable.subject_id)
            .filter(Timetable.teacher_id == teacher.id, Timetable.school_id == school_id)
            .distinct()
            .all()
        ):
            slots.add((row[0], row[1], row[2]))

        for row in (
            db.query(TeacherSubject.grade_id, TeacherSubject.section_id, TeacherSubject.subject_id)
            .filter(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.school_id == school_id,
            )
            .distinct()
            .all()
        ):
            slots.add((row[0], row[1], row[2]))

        return slots

    @classmethod
    def teacher_is_assigned(
        cls,
        db: Session,
        *,
        teacher: Teacher,
        school_id: int,
        grade_id: int,
        section_id: int,
        subject_id: int,
    ) -> bool:
        if not cls._targets_in_school(
            db,
            school_id=school_id,
            grade_id=grade_id,
            section_id=section_id,
            subject_id=subject_id,
        ):
            return False
        return (grade_id, section_id, subject_id) in cls.teacher_assignments(db, teacher, school_id)

    @staticmethod
    def _validate_scheduled_date(
        scheduled_date: date, year: AcademicYear, *, field: str = "scheduled_date"
    ) -> None:
        """Not in the past (today is allowed) and inside the academic year."""
        today = date.today()
        if scheduled_date < today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be in the past (today is {today.isoformat()})",
            )
        if scheduled_date < year.start_date or scheduled_date > year.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{field} must fall inside the academic year "
                    f"{year.name} ({year.start_date.isoformat()} to {year.end_date.isoformat()})"
                ),
            )

    # -- display names -------------------------------------------------------

    @staticmethod
    def _load_names(db: Session, rows: Sequence[SlipTest]) -> None:
        """Attach grade/section/subject/teacher display names to ``rows``.

        Four bulk queries regardless of list length — the same approach
        ``app/routers/v1/homework.py::_enrich_with_names`` uses.
        """
        if not rows:
            return

        grade_ids = {r.grade_id for r in rows}
        section_ids = {r.section_id for r in rows}
        subject_ids = {r.subject_id for r in rows}
        teacher_ids = {r.teacher_id for r in rows}

        grades = {g.id: g.name for g in db.query(Grade).filter(Grade.id.in_(grade_ids)).all()}
        sections = {s.id: s.name for s in db.query(Section).filter(Section.id.in_(section_ids)).all()}
        subjects = {s.id: s.name for s in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()}

        teacher_names: Dict[int, Optional[str]] = {}
        if teacher_ids:
            teacher_rows = db.query(Teacher).filter(Teacher.id.in_(teacher_ids)).all()
            user_ids = [t.user_id for t in teacher_rows if t.user_id]
            users = {
                u.id: u.display_name
                for u in db.query(User).filter(User.id.in_(user_ids)).all()
            } if user_ids else {}
            teacher_names = {t.id: users.get(t.user_id) for t in teacher_rows}

        for row in rows:
            row.grade_name = grades.get(row.grade_id)
            row.section_name = sections.get(row.section_id)
            row.subject_name = subjects.get(row.subject_id)
            row.teacher_name = teacher_names.get(row.teacher_id)

    @staticmethod
    def _serialize(
        rows: Sequence[SlipTest],
        *,
        duplicate_warning: Optional[str] = None,
    ) -> List[SlipTestResponse]:
        """``is_past`` is derived per request from the school-local today, so a
        test moves from "Upcoming" to "Past" by itself once its date passes —
        no background job has to write to the row."""
        today = date.today()
        return [
            SlipTestResponse(
                id=row.id,
                school_id=row.school_id,
                academic_year_id=row.academic_year_id,
                grade_id=row.grade_id,
                section_id=row.section_id,
                subject_id=row.subject_id,
                teacher_id=row.teacher_id,
                title=row.title,
                description=row.description,
                scheduled_date=row.scheduled_date,
                start_time=row.start_time,
                duration_minutes=row.duration_minutes,
                max_marks=row.max_marks,
                status=str(row.status),
                created_at=row.created_at,
                updated_at=row.updated_at,
                grade_name=getattr(row, "grade_name", None),
                section_name=getattr(row, "section_name", None),
                subject_name=getattr(row, "subject_name", None),
                teacher_name=getattr(row, "teacher_name", None),
                is_past=row.scheduled_date < today,
                duplicate_warning=duplicate_warning,
            )
            for row in rows
        ]

    @classmethod
    def _serialize_one(cls, db: Session, row: SlipTest) -> SlipTestResponse:
        """Single-row convenience wrapper — the bulk name loader handles a
        one-element sequence just as happily as a page of them."""
        cls._load_names(db, [row])
        return cls._serialize([row])[0]

    # -- teacher: class cards ------------------------------------------------

    @classmethod
    def list_teacher_classes(
        cls, db: Session, *, teacher: Teacher, school_id: int, academic_year_id: Optional[int]
    ) -> List[SlipTestClassCard]:
        """One card per class + subject this teacher is assigned to, with the
        number of still-upcoming tests she created for it.

        An assignment with no students and no tests is still listed — it is a
        real teaching slot, it simply has nothing scheduled yet.
        """
        repo = SlipTestRepository(db)
        today = date.today()

        slots = cls.teacher_assignments(db, teacher, school_id)
        if not slots:
            return []

        grade_ids = {g for g, _, _ in slots}
        section_ids = {s for _, s, _ in slots}
        subject_ids = {sub for _, _, sub in slots}

        grades = {g.id: g.name for g in db.query(Grade).filter(Grade.id.in_(grade_ids)).all()}
        sections = {s.id: s.name for s in db.query(Section).filter(Section.id.in_(section_ids)).all()}
        subjects = {s.id: s.name for s in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()}

        # `upcoming_counts_by_slot` yields (grade_id, section_id, subject_id, count).
        upcoming = {
            (grade_id, section_id, subject_id): count
            for grade_id, section_id, subject_id, count in repo.upcoming_counts_by_slot(
                school_id=school_id,
                academic_year_id=academic_year_id,
                today=today,
                teacher_id=teacher.id,
            )
        }

        cards: List[SlipTestClassCard] = []
        for grade_id, section_id, subject_id in sorted(slots):
            grade_name = grades.get(grade_id)
            section_name = sections.get(section_id)
            subject_name = subjects.get(subject_id)
            label = " - ".join(
                part for part in [grade_name, section_name] if part
            ) or f"Grade {grade_id} - Section {section_id}"
            cards.append(
                SlipTestClassCard(
                    grade_id=grade_id,
                    grade_name=grade_name,
                    section_id=section_id,
                    section_name=section_name,
                    subject_id=subject_id,
                    subject_name=subject_name,
                    display_name=f"{label} - {subject_name or f'Subject {subject_id}'}",
                    upcoming_count=upcoming.get((grade_id, section_id, subject_id), 0),
                    total_count=repo.count(
                        school_id=school_id,
                        teacher_id=teacher.id,
                        academic_year_id=academic_year_id,
                        grade_id=grade_id,
                        section_id=section_id,
                        subject_id=subject_id,
                    ),
                )
            )
        return cards

    # -- teacher: list / detail ---------------------------------------------

    @classmethod
    def list_for_teacher(
        cls,
        db: Session,
        *,
        teacher: Teacher,
        school_id: int,
        academic_year_id: Optional[int],
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        # Named `lifecycle` rather than `status` on purpose: a parameter called
        # `status` shadows the `fastapi.status` module used for the HTTP status
        # codes a few lines below.
        lifecycle: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[SlipTestResponse], int]:
        """Slip tests **this teacher created**, in her own school and year.

        When a class/subject filter is supplied it must be one she is assigned
        to, otherwise 403 — she cannot use the list endpoint to probe classes
        she does not teach.
        """
        if lifecycle:
            lifecycle = str(lifecycle).strip().lower()
            if lifecycle not in SLIP_TEST_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"status must be one of: {', '.join(SLIP_TEST_STATUSES)}",
                )

        if section_id is not None or subject_id is not None:
            grade_id = grade_id if grade_id is not None else _grade_of_section(db, school_id, section_id)
            if grade_id is None or subject_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Filtering by class requires a valid class and a subject",
                )
            if not cls.teacher_is_assigned(
                db,
                teacher=teacher,
                school_id=school_id,
                grade_id=grade_id,
                section_id=section_id,
                subject_id=subject_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to this class and subject",
                )

        repo = SlipTestRepository(db)
        filters = dict(
            school_id=school_id,
            teacher_id=teacher.id,
            academic_year_id=academic_year_id,
            grade_id=grade_id,
            section_id=section_id,
            subject_id=subject_id,
            status=lifecycle,
        )
        rows = repo.list(skip=skip, limit=limit, **filters)
        total = repo.count(**filters)
        cls._load_names(db, rows)
        return cls._serialize(rows), total

    @classmethod
    def _owned_or_404(
        cls, db: Session, *, slip_test_id: int, school_id: int, teacher: Teacher
    ) -> SlipTest:
        """Load a slip test the teacher is allowed to touch.

        Cross-school and not-mine both answer 404, not 403: a different answer
        would confirm the row exists. This mirrors
        ``HomeworkService.update_homework``'s behaviour.
        """
        row = crud_slip_test.get(db, slip_test_id)
        if not row or row.school_id != school_id or row.teacher_id != teacher.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Slip test not found"
            )
        return row

    # -- teacher: create -----------------------------------------------------

    @classmethod
    def create_slip_test(
        cls,
        db: Session,
        *,
        obj_in: SlipTestCreate,
        teacher: Teacher,
        teacher_user: User,
        school_id: int,
        academic_year_id: Optional[int],
    ) -> Tuple[SlipTestResponse, int]:
        """Create + notify in one transaction. Returns ``(row, notified_count)``."""
        year = cls.require_open_academic_year(db, academic_year_id)

        if not cls.teacher_is_assigned(
            db,
            teacher=teacher,
            school_id=school_id,
            grade_id=obj_in.grade_id,
            section_id=obj_in.section_id,
            subject_id=obj_in.subject_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this class and subject",
            )

        cls._validate_scheduled_date(obj_in.scheduled_date, year)

        title = sanitize_text(obj_in.title, 150)
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="title is required"
            )
        description = sanitize_text(obj_in.description, MAX_DESCRIPTION_LENGTH)

        # Warn but allow: two tests for one class+subject+date is unusual, not
        # forbidden (a teacher may genuinely run two short tests in a day).
        same_slot = crud_slip_test.find_same_slot_on_date(
            db,
            school_id=school_id,
            academic_year_id=year.id,
            grade_id=obj_in.grade_id,
            section_id=obj_in.section_id,
            subject_id=obj_in.subject_id,
            scheduled_date=obj_in.scheduled_date,
        )
        warning = (
            "Another slip test already exists for this class and subject on that date."
            if same_slot
            else None
        )

        repo = SlipTestRepository(db)
        try:
            row = repo.create(
                school_id=school_id,
                academic_year_id=year.id,
                grade_id=obj_in.grade_id,
                section_id=obj_in.section_id,
                subject_id=obj_in.subject_id,
                teacher_id=teacher.id,
                title=title,
                description=description,
                scheduled_date=obj_in.scheduled_date,
                start_time=obj_in.start_time,
                duration_minutes=obj_in.duration_minutes,
                max_marks=obj_in.max_marks,
                status=DEFAULT_SLIP_TEST_STATUS,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            subject_name = _name_of(db, Subject, obj_in.subject_id)
            notified = _fan_out(
                db,
                row,
                recipients=cls._recipients(db, school_id=school_id, section_id=row.section_id,
                                            academic_year_id=year.id),
                sender=teacher_user,
                title="New slip test",
                message=(
                    f"New slip test: {subject_name or 'a subject'} on {_when_label(row)} "
                    f"({row.max_marks} marks). {row.title}"
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(row)
        serialized = cls._serialize_one(db, row)
        # Advisory only - the row was created regardless.
        serialized.duplicate_warning = warning
        return serialized, notified

    # -- teacher: update -----------------------------------------------------

    @classmethod
    def update_slip_test(
        cls,
        db: Session,
        *,
        slip_test_id: int,
        obj_in: SlipTestUpdate,
        teacher: Teacher,
        teacher_user: User,
        school_id: int,
    ) -> Tuple[SlipTestResponse, int]:
        """Edit + notify in one transaction.

        The row's own academic year decides which year rules apply — a test
        always stays in the year it was created in, so editing can never move it
        into a closed year.
        """
        repo = SlipTestRepository(db)
        row = cls._owned_or_404(
            db, slip_test_id=slip_test_id, school_id=school_id, teacher=teacher
        )

        if str(row.status).lower() == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This slip test has been cancelled and can no longer be edited",
            )

        year = cls.require_open_academic_year(db, row.academic_year_id)
        changes = obj_in.model_dump(exclude_unset=True)
        if not changes:
            return cls._serialize_one(db, row), 0

        values: Dict[str, object] = {}

        if "title" in changes:
            title = sanitize_text(changes["title"], 150)
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="title is required"
                )
            values["title"] = title

        if "description" in changes:
            values["description"] = sanitize_text(
                changes["description"], MAX_DESCRIPTION_LENGTH
            )

        if "scheduled_date" in changes and changes["scheduled_date"] is not None:
            cls._validate_scheduled_date(changes["scheduled_date"], year)
            values["scheduled_date"] = changes["scheduled_date"]

        if "start_time" in changes:
            values["start_time"] = changes["start_time"]
        if "duration_minutes" in changes:
            values["duration_minutes"] = changes["duration_minutes"]
        if "max_marks" in changes and changes["max_marks"] is not None:
            values["max_marks"] = changes["max_marks"]

        # Only a change students care about earns a notification. Renaming a
        # test is not newsworthy; moving it is.
        notified_fields = {"scheduled_date", "start_time", "duration_minutes",
                           "max_marks", "description"}
        notify = bool(notified_fields & set(values))

        if not notify:
            values["updated_at"] = datetime.utcnow()
            try:
                repo.update(row, values)
                db.commit()
            except Exception:
                db.rollback()
                raise
            db.refresh(row)
            return cls._serialize_one(db, row), 0

        # Same-slot advisory, computed against the *new* date.
        new_date = values.get("scheduled_date", row.scheduled_date)
        same_slot = crud_slip_test.find_same_slot_on_date(
            db,
            school_id=school_id,
            academic_year_id=row.academic_year_id,
            grade_id=row.grade_id,
            section_id=row.section_id,
            subject_id=row.subject_id,
            scheduled_date=new_date,
            exclude_id=row.id,
        )
        warning = (
            "Another slip test already exists for this class and subject on that date."
            if same_slot
            else None
        )

        try:
            values["updated_at"] = datetime.utcnow()
            repo.update(row, values)
            db.refresh(row)

            subject_name = _name_of(db, Subject, row.subject_id)
            notified = _fan_out(
                db,
                row,
                recipients=cls._recipients(
                    db, school_id=school_id, section_id=row.section_id,
                    academic_year_id=row.academic_year_id,
                ),
                sender=teacher_user,
                title="Slip test updated",
                message=(
                    f"Slip test updated: {subject_name or 'a subject'} is now on "
                    f"{_when_label(row)} ({row.max_marks} marks). {_changed_summary(values)}"
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(row)
        serialized = cls._serialize_one(db, row)
        serialized.duplicate_warning = warning
        return serialized, notified

    # -- teacher: cancel (soft) ---------------------------------------------

    @classmethod
    def cancel_slip_test(
        cls,
        db: Session,
        *,
        slip_test_id: int,
        teacher: Teacher,
        teacher_user: User,
        school_id: int,
    ) -> Tuple[SlipTestResponse, int]:
        """Soft cancel — the row and its history are never deleted.

        Idempotent: cancelling an already-cancelled test succeeds silently and
        sends no second notification, so a double tap (or a retry after a flaky
        response) cannot spam a class.
        """
        repo = SlipTestRepository(db)
        row = cls._owned_or_404(
            db, slip_test_id=slip_test_id, school_id=school_id, teacher=teacher
        )

        if str(row.status).lower() == "cancelled":
            return cls._serialize_one(db, row), 0

        try:
            repo.update(
                row, {"status": "cancelled", "updated_at": datetime.utcnow()}
            )
            db.refresh(row)

            subject_name = _name_of(db, Subject, row.subject_id)
            notified = _fan_out(
                db,
                row,
                recipients=cls._recipients(
                    db, school_id=school_id, section_id=row.section_id,
                    academic_year_id=row.academic_year_id,
                ),
                sender=teacher_user,
                title="Slip test cancelled",
                message=(
                    f"Slip test cancelled: {subject_name or 'a subject'} on "
                    f"{_format_date(row.scheduled_date)} ({row.title}) will not take place."
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(row)
        return cls._serialize_one(db, row), notified

    # -- student: read-only --------------------------------------------------

    @classmethod
    def _student_section_ids(
        cls, db: Session, student: Student, academic_year_id: Optional[int]
    ) -> List[int]:
        """Sections this student is enrolled in **for the resolved year**.

        ``student_enrollments`` is unique on ``(student_id, academic_year_id)``,
        so scoping by year is what makes "transferred or re-enrolled mid-year"
        correct: the student only ever sees the class they are in *now*, for the
        year being viewed.
        """
        query = db.query(StudentEnrollment.section_id).filter(
            StudentEnrollment.student_id == student.id
        )
        if academic_year_id is not None:
            query = query.filter(StudentEnrollment.academic_year_id == academic_year_id)
        return [row[0] for row in query.distinct().all()]

    @classmethod
    def list_for_student(
        cls,
        db: Session,
        *,
        student: Student,
        school_id: int,
        academic_year_id: Optional[int],
        time_filter: str = "upcoming",
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[SlipTestResponse], int]:
        """Read-only listing, hard-scoped to the student's own sections.

        Cancelled tests are **included** in every filter — students must be able
        to see that something they were told about will not happen. The
        ``status`` field carries the cancellation and the UI renders a badge.
        """
        section_ids = cls._student_section_ids(db, student, academic_year_id)
        if not section_ids:
            return [], 0

        today = date.today()
        if time_filter == "upcoming":
            date_from, date_to = today, None
        elif time_filter == "past":
            date_from, date_to = None, today - timedelta(days=1)
        else:  # "all"
            date_from, date_to = None, None

        repo = SlipTestRepository(db)
        rows: List[SlipTest] = []
        total = 0
        # One query per section keeps the row set identical to the ids we just
        # authorised, so there is no way for the query to widen the audience.
        # `skip + limit` rows are pulled per section and the window is applied
        # ONCE after merging: slicing inside the loop would paginate each
        # section separately and drop rows the caller asked for.
        for section_id in section_ids:
            filters = dict(
                school_id=school_id,
                section_id=section_id,
                academic_year_id=academic_year_id,
                date_from=date_from,
                date_to=date_to,
            )
            rows.extend(repo.list(skip=0, limit=skip + limit, **filters))
            total += repo.count(**filters)

        rows.sort(key=lambda r: (r.scheduled_date, r.start_time or _midnight(), r.id))
        page = rows[skip : skip + limit] if (skip or limit) else rows
        cls._load_names(db, page)
        return cls._serialize(page), total

    @classmethod
    def get_for_student(
        cls,
        db: Session,
        *,
        slip_test_id: int,
        student: Student,
        school_id: int,
        academic_year_id: Optional[int],
    ) -> Optional[SlipTestResponse]:
        row = crud_slip_test.get(db, slip_test_id)
        if not row:
            return None
        # school first, then the student's own sections: another class's test is
        # simply "not found", never "forbidden", so nothing is leaked.
        if row.school_id != school_id:
            return None
        if academic_year_id is not None and row.academic_year_id != academic_year_id:
            return None
        if row.section_id not in cls._student_section_ids(db, student, academic_year_id):
            return None
        return cls._serialize_one(db, row)

    # -- notifications -------------------------------------------------------

    @staticmethod
    def _recipients(
        db: Session, *, school_id: int, section_id: int, academic_year_id: int
    ) -> List[Tuple[int, int]]:
        """``(student_id, user_id)`` for every ACTIVE student of that section in
        that year.

        Excluded on purpose:
        * students of any other section (the enrolment join enforces it),
        * inactive accounts (``users.account_status != 'ACTIVE'``),
        * inactive students (``students.student_status`` not ACTIVE/NULL).

        An empty class is a perfectly normal state — the caller notifies nobody
        and still succeeds.
        """
        rows = (
            db.query(Student.id, User.id)
            .join(StudentEnrollment, StudentEnrollment.student_id == Student.id)
            .join(User, User.id == Student.user_id)
            .filter(
                StudentEnrollment.section_id == section_id,
                StudentEnrollment.academic_year_id == academic_year_id,
                Student.school_id == school_id,
                User.school_id == school_id,
                func.upper(User.is_active) == "ACTIVE",
                or_(
                    Student.student_status.is_(None),
                    func.upper(Student.student_status) == "ACTIVE",
                ),
            )
            .distinct()
            .all()
        )
        return [(row[0], row[1]) for row in rows]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _midnight() -> dt_time:
    """Sorts a NULL ``start_time`` after real times on the same day."""
    return dt_time(0, 0)


def _name_of(db: Session, model, row_id: Optional[int]) -> Optional[str]:
    if not row_id:
        return None
    return db.query(model.name).filter(model.id == row_id).scalar()


def _grade_of_section(db: Session, school_id: int, section_id: Optional[int]) -> Optional[int]:
    if section_id is None:
        return None
    return (
        db.query(Section.grade_id)
        .filter(Section.id == section_id, Section.school_id == school_id)
        .scalar()
    )


def _changed_summary(values: Dict[str, object]) -> str:
    labels = {
        "scheduled_date": "date",
        "start_time": "time",
        "duration_minutes": "duration",
        "max_marks": "maximum marks",
        "description": "topics",
    }
    changed = [label for field, label in labels.items() if field in values]
    return "Updated: " + ", ".join(changed) if changed else "Details updated"


def _fan_out(
    db: Session,
    row: SlipTest,
    *,
    recipients: Iterable[Tuple[int, int]],
    sender: User,
    title: str,
    message: str,
) -> int:
    """Add one notification per recipient inside the caller's transaction.

    ``db.add`` only — never ``db.commit``. The caller commits once, so the slip
    test write and the whole fan-out succeed or fail together.

    ``reference_id`` carries the slip test id, which is what lets a student tap
    the bell entry and land on the detail screen.
    """
    count = 0
    for student_id, user_id in recipients:
        db.add(
            Notification(
                school_id=row.school_id,
                sender_id=sender.id,
                sender_role="TEACHER",
                notification_type=SLIP_TEST_NOTIFICATION_TYPE,
                category=SLIP_TEST_NOTIFICATION_CATEGORY,
                title=title,
                message=message,
                target_class_id=row.section_id,
                target_student_id=student_id,
                user_id=user_id,
                reference_id=row.id,
                is_read=False,
            )
        )
        count += 1
    return count


slip_test_service = SlipTestService()