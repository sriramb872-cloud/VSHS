# backend-python/app/routers/v1/slip_tests.py
"""Slip tests — REST API for exactly two roles.

Mounted under the app's ``/api/v1`` prefix (see ``main.py``) as two routers so
the role prefixes stay honest and self-documenting:

* ``/api/v1/teacher/slip-tests``  — create / edit / cancel
* ``/api/v1/student/slip-tests``  — read-only

Principal and Super Admin have **no** slip test surface. Unlike the shared
``deps.require_roles`` helper, which deliberately lets SUPER_ADMIN through
everything, the guard below compares the role exactly. That is the point of the
feature: slip tests are strictly between teacher and student.

The routers only translate HTTP into service calls; every authorization and
validation decision is made in ``app/services/slip_test.py``.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api import deps
from app.api.year_context import resolve_year_id
from app.models.slip_test import SLIP_TEST_STATUSES
from app.models.user import User
from app.schemas.slip_test import (
    SlipTestClassListResponse,
    SlipTestCreate,
    SlipTestListResponse,
    SlipTestResponse,
    SlipTestUpdate,
)
from app.services.slip_test import SlipTestService


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------


def require_teacher(current_user: User = Depends(deps.get_current_active_user)) -> User:
    """TEACHER only.

    Deliberately not ``deps.require_roles(['TEACHER'])``: that helper grants
    SUPER_ADMIN an unconditional bypass, which would hand the platform operator
    a slip test API this feature deliberately does not expose.
    """
    if str(current_user.role).upper() != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Slip tests are available to teachers only",
        )
    return current_user


def require_student(current_user: User = Depends(deps.get_current_active_user)) -> User:
    """STUDENT only, same reasoning as :func:`require_teacher`."""
    if str(current_user.role).upper() != "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Slip tests are available to students only",
        )
    return current_user


router = APIRouter(
    prefix="/teacher/slip-tests",
    tags=["Slip Tests (Teacher)"],
    dependencies=[Depends(deps.require_subscription_access)],
)

student_router = APIRouter(
    prefix="/student/slip-tests",
    tags=["Slip Tests (Student)"],
    dependencies=[Depends(deps.require_subscription_access)],
)


# ---------------------------------------------------------------------------
# Teacher
# ---------------------------------------------------------------------------


@router.get("/classes", response_model=SlipTestClassListResponse)
def list_my_slip_test_classes(
    request: Request = None,
    academic_year_id: Optional[int] = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_teacher),
):
    """The class + subject cards shown on the teacher's landing page.

    Built entirely from the existing teacher assignment (timetable rows and/or
    explicit teacher-subject rows) — see the service module docstring.
    """
    teacher = SlipTestService.get_teacher_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School context not found"
        )

    year_id = _resolve_year(db, current_user, request, academic_year_id)
    cards = SlipTestService.list_teacher_classes(
        db, teacher=teacher, school_id=school_id, academic_year_id=year_id
    )
    return {"total": len(cards), "items": cards}


@router.get("", response_model=SlipTestListResponse)
def list_teacher_slip_tests(
    request: Request = None,
    academic_year_id: Optional[int] = Query(None),
    class_: Optional[int] = Query(
        None,
        alias="class",
        description="Section (class) id. Only combinations this teacher is assigned to are accepted.",
    ),
    section_id: Optional[int] = Query(
        None, description="Explicit alias for `class`; used when both are absent."
    ),
    subject: Optional[int] = Query(None, description="Subject id"),
    subject_id: Optional[int] = Query(None, description="Explicit alias for `subject`"),
    status_filter: Optional[str] = Query(
        None, alias="status", description=f"One of: {', '.join(SLIP_TEST_STATUSES)}"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_teacher),
):
    """Slip tests this teacher created, in their own school and academic year."""
    teacher = SlipTestService.get_teacher_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School context not found"
        )

    year_id = _resolve_year(db, current_user, request, academic_year_id)
    items, total = SlipTestService.list_for_teacher(
        db,
        teacher=teacher,
        school_id=school_id,
        academic_year_id=year_id,
        grade_id=None,
        section_id=class_ if class_ is not None else section_id,
        subject_id=subject if subject is not None else subject_id,
        lifecycle=status_filter,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "items": items}


@router.get("/{slip_test_id}", response_model=SlipTestResponse)
def get_my_slip_test(
    slip_test_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_teacher),
):
    """Detail view. 404 for another teacher's test or another school's — never
    403, which would confirm the row exists."""
    teacher = SlipTestService.get_teacher_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School context not found"
        )
    row = SlipTestService._owned_or_404(
        db, slip_test_id=slip_test_id, school_id=school_id, teacher=teacher
    )
    return SlipTestService._serialize_one(row)


@router.post("", response_model=SlipTestResponse, status_code=status.HTTP_201_CREATED)
def create_slip_test(
    obj_in: SlipTestCreate,
    request: Request = None,
    academic_year_id: Optional[int] = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_teacher),
):
    """Schedule a slip test for a class + subject the teacher is assigned to.

    Responds with the created row. When another test already exists for the same
    class + subject + date, ``duplicate_warning`` is set — advisory only, the
    create still succeeds.
    """
    teacher = SlipTestService.get_teacher_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="School context not found"
        )

    # Payload first (explicit choice wins), then header/active year.
    year_id = obj_in.academic_year_id
    if year_id is None:
        year_id = _resolve_year(db, current_user, request, academic_year_id)

    created, notified = SlipTestService.create_slip_test(
        db,
        obj_in=obj_in,
        teacher=teacher,
        teacher_user=current_user,
        school_id=school_id,
        academic_year_id=year_id,
    )
    return created


@router.put("/{slip_test_id}", response_model=SlipTestResponse)
def update_slip_test(
    slip_test_id: int,
    obj_in: SlipTestUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_teacher),
):
    """Edit a slip test the caller created.

    Editing a cancelled test is a 409, not a silent no-op: the caller needs to
    know their change was rejected rather than assume it applied.
    """
    teacher = SlipTestService.get_teacher_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="School context not found"
        )

    updated, _notified = SlipTestService.update_slip_test(
        db,
        slip_test_id=slip_test_id,
        obj_in=obj_in,
        teacher=teacher,
        teacher_user=current_user,
        school_id=school_id,
    )
    return updated


@router.post("/{slip_test_id}/cancel", response_model=SlipTestResponse)
def cancel_slip_test(
    slip_test_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_teacher),
):
    """Soft cancel. The row and its notification history are never deleted, so a
    cancelled test stays visible to students, clearly marked."""
    teacher = SlipTestService.get_teacher_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="School context not found"
        )

    cancelled, _notified = SlipTestService.cancel_slip_test(
        db,
        slip_test_id=slip_test_id,
        teacher=teacher,
        teacher_user=current_user,
        school_id=school_id,
    )
    return cancelled


# ---------------------------------------------------------------------------
# Student (read-only)
# ---------------------------------------------------------------------------


@student_router.get("", response_model=SlipTestListResponse)
def list_student_slip_tests(
    request: Request = None,
    academic_year_id: Optional[int] = Query(None),
    filter: str = Query(
        "upcoming",
        pattern="^(upcoming|past|all)$",
        description="upcoming = today onwards, past = strictly before today, all = everything",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_student),
):
    """Slip tests for the student's **own** class/section in the resolved year.

    The split is derived from the school-local date at request time, so a test
    moves from Upcoming to Past on its own. Cancelled tests appear in every
    filter, flagged via ``status``.
    """
    student = SlipTestService.get_student_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School context not found"
        )

    year_id = _resolve_year(db, current_user, request, academic_year_id)
    items, total = SlipTestService.list_for_student(
        db,
        student=student,
        school_id=school_id,
        academic_year_id=year_id,
        time_filter=filter,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "items": items}


@student_router.get("/{slip_test_id}", response_model=SlipTestResponse)
def get_slip_test(
    slip_test_id: int,
    request: Request = None,
    academic_year_id: Optional[int] = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_student),
):
    """Detail view, used as the notification deep-link target.

    Another class's test, another school's test and a test from a different
    academic year all answer 404 — the endpoint can never be used to confirm
    that someone else's test exists.
    """
    student = SlipTestService.get_student_for_user(db, current_user)
    school_id = deps.scoped_school_id(current_user)
    if not school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School context not found"
        )

    year_id = _resolve_year(db, current_user, request, academic_year_id)
    found = SlipTestService.get_for_student(
        db,
        slip_test_id=slip_test_id,
        student=student,
        school_id=school_id,
        academic_year_id=year_id,
    )
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Slip test not found"
        )
    return found


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


def _resolve_year(
    db: Session, current_user: User, request: Optional[Request], explicit: Optional[int]
) -> Optional[int]:
    """One academic year per request, validated against the caller's school.

    Delegates to the project-wide resolver (explicit param → ``X-Academic-Year-Id``
    header → school ACTIVE year) so slip tests behave exactly like every other
    year-scoped screen.
    """
    return resolve_year_id(
        db, current_user, request, explicit=explicit, allow_all=False
    )