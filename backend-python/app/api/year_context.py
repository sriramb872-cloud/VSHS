# backend-python/app/api/year_context.py
"""Per-request academic year resolution.

Every year-scoped endpoint resolves *one* academic year for the request using
the same, auditable rule:

1. an explicit ``academic_year_id`` query parameter (``0`` is the documented
   "all years" sentinel and resolves to ``None`` without any lookup),
2. otherwise the ``X-Academic-Year-Id`` request header,
3. otherwise the authenticated user's school ACTIVE year.

Whatever the source, the resolved year is *always* validated: it must exist
(404) and it must belong to the authenticated user's school (403) unless the
caller is a SUPER_ADMIN. That check is what prevents a teacher from pointing
the header at another school's year and reading its roster, marks or exams.
"""
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear
from app.models.user import User

ACADEMIC_YEAR_HEADER = "X-Academic-Year-Id"
ALL_YEARS_SENTINEL = 0


def get_school_active_year(db: Session, school_id: Optional[int]) -> Optional[AcademicYear]:
    """The year a school is currently running.

    Prefers ``status == 'ACTIVE'``; falls back to the year containing today
    and then to the most recently started year so that schools whose years
    were all closed before this feature existed still resolve to something
    sensible instead of erroring on every request.
    """
    if not school_id:
        return None

    active = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.school_id == school_id,
            AcademicYear.status == "ACTIVE",
        )
        .first()
    )
    if active is not None:
        return active

    from datetime import date as _date

    today = _date.today()
    containing = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.school_id == school_id,
            AcademicYear.start_date <= today,
            AcademicYear.end_date >= today,
        )
        .order_by(AcademicYear.start_date.desc())
        .first()
    )
    if containing is not None:
        return containing

    return (
        db.query(AcademicYear)
        .filter(AcademicYear.school_id == school_id)
        .order_by(AcademicYear.start_date.desc(), AcademicYear.id.desc())
        .first()
    )


def _validate_school(year: AcademicYear, current_user: User) -> None:
    """Reject any year that does not belong to the caller's school."""
    role = str(getattr(current_user, "role", "")).upper()
    if role == "SUPER_ADMIN":
        return
    if not current_user.school_id or year.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Academic year does not belong to your school",
        )


def _parse_explicit(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="academic_year_id must be an integer",
        )


def resolve_academic_year(
    db: Session,
    current_user: User,
    request: Optional[Request] = None,
    explicit: Optional[object] = None,
    allow_all: bool = True,
) -> Optional[AcademicYear]:
    """Resolve the academic year for this request (see module docstring).

    Returns ``None`` only when the caller explicitly asked for "all years"
    (``academic_year_id=0``) and ``allow_all`` is true; in every other case a
    year is returned if the school has one at all.
    """
    from fastapi import HTTPException, status

    resolved_id: Optional[int] = None
    sentinel = False

    if explicit is not None:
        parsed = _parse_explicit(str(explicit))
        if parsed == ALL_YEARS_SENTINEL:
            if allow_all:
                sentinel = True
            # else: the caller does not accept "all years"; ignore the
            # sentinel and fall through to header/active-year resolution.
        elif parsed is not None:
            resolved_id = parsed

    if sentinel:
        return None

    if resolved_id is None and request is not None:
        header_value = request.headers.get(ACADEMIC_YEAR_HEADER)
        if header_value not in (None, ""):
            parsed = _parse_explicit(header_value)
            if parsed == ALL_YEARS_SENTINEL:
                if allow_all:
                    return None
            else:
                resolved_id = parsed

    if resolved_id is None:
        # No explicit choice: use the school's active year.
        school_id = current_user.school_id
        role = str(getattr(current_user, "role", "")).upper()
        if role == "SUPER_ADMIN" and not school_id:
            # Super admins without a school context have no "their" year.
            return None
        return get_school_active_year(db, school_id)

    year = db.query(AcademicYear).filter(AcademicYear.id == resolved_id).first()
    if year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic year not found",
        )
    _validate_school(year, current_user)
    return year


def resolve_year_id(
    db: Session,
    current_user: User,
    request: Optional[Request] = None,
    explicit: Optional[object] = None,
    allow_all: bool = True,
) -> Optional[int]:
    """Convenience wrapper returning just the id (or ``None``)."""
    year = resolve_academic_year(db, current_user, request, explicit, allow_all)
    return year.id if year is not None else None
