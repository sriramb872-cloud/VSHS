# backend-python/app/schemas/slip_test.py
"""Pydantic schemas for the Slip Tests feature.

Validation that needs the database (does the grade belong to this school? is the
teacher actually assigned to this class + subject?) lives in
``app/services/slip_test.py`` — these schemas only enforce what can be checked
from the payload alone, so the client gets field-level errors before any query
runs.

Bounds
------
* ``title``            1..150 characters (matches the ``VARCHAR(150)`` column)
* ``description``      optional, max 1000 characters
* ``max_marks``        1..1000. A slip test is a short quiz; anything above 1000
                       is a data-entry mistake, not a test.
* ``duration_minutes`` 1..600 when supplied
* ``scheduled_date``   cannot be in the past and must fall inside the academic
                       year — both need the resolved ``AcademicYear`` row, so
                       they are enforced in the service.
"""
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator

#: Allowed lifecycle values, imported from the model so the schema and the
#: storage layer can never disagree about what a status may be.

#: Upper bound for `max_marks`. Documented in the module docstring.
MAX_MARKS_LIMIT = 1000
#: Upper bound for `duration_minutes` (10 hours).
MAX_DURATION_MINUTES = 600
#: Upper bound for `description` (syllabus / topics).
MAX_DESCRIPTION_LENGTH = 1000


class SlipTestBase(BaseModel):
    grade_id: int = Field(..., description="Grade the test is for")
    section_id: int = Field(..., description="Section (class) the test is for")
    subject_id: int = Field(..., description="Subject being tested")

    title: str = Field(..., min_length=1, max_length=150, description="Short test title")
    description: Optional[str] = Field(
        None, max_length=MAX_DESCRIPTION_LENGTH, description="Syllabus / topics covered"
    )

    scheduled_date: date = Field(..., description="School-local date the test is held")
    start_time: Optional[time] = Field(None, description="Optional start time")
    duration_minutes: Optional[int] = Field(
        None, ge=1, le=MAX_DURATION_MINUTES, description="Optional duration in minutes"
    )

    max_marks: int = Field(..., ge=1, le=MAX_MARKS_LIMIT, description="Maximum / total marks")

    academic_year_id: Optional[int] = Field(
        None,
        description=(
            "Academic year. Optional on create — the service falls back to the "
            "year resolved from the request context (header / active year)."
        ),
    )

    @field_validator("title", "description")
    @classmethod
    def _strip_text(cls, value):
        """Trim surrounding whitespace so a title of `"   "` cannot pass the
        length check and then render as a blank card."""
        if value is None:
            return None
        return value.strip()


class SlipTestCreate(SlipTestBase):
    pass


class SlipTestUpdate(BaseModel):
    """Every field optional — this is a PATCH-shaped payload used by the PUT
    endpoint. Only the fields actually present are applied, so an omitted field
    is never silently reset to a default."""

    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
    scheduled_date: Optional[date] = None
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=MAX_DURATION_MINUTES)
    max_marks: Optional[int] = Field(None, ge=1, le=MAX_MARKS_LIMIT)

    @field_validator("title", "description")
    @classmethod
    def _strip_text(cls, value):
        if value is None:
            return None
        return value.strip()


class SlipTestResponse(BaseModel):
    id: int
    school_id: int
    academic_year_id: int
    grade_id: int
    section_id: int
    subject_id: int
    teacher_id: int

    title: str
    description: Optional[str] = None
    scheduled_date: date
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    max_marks: int
    status: str

    created_at: datetime
    updated_at: Optional[datetime] = None

    # Display names, joined in bulk by the service (never N+1 — the list
    # endpoints fetch every needed name in one query per entity type).
    grade_name: Optional[str] = None
    section_name: Optional[str] = None
    subject_name: Optional[str] = None
    teacher_name: Optional[str] = None

    #: True when `scheduled_date` is strictly before the school-local today.
    #: Derived per request so a test moves from "Upcoming" to "Past" on its own
    #: without any background job writing to the row.
    is_past: bool = False

    #: Non-blocking advisory set when another slip test already exists for the
    #: same class + subject + date. The create still succeeds.
    duplicate_warning: Optional[str] = None

    class Config:
        from_attributes = True


class SlipTestListResponse(BaseModel):
    total: int
    items: list[SlipTestResponse]


class SlipTestClassCard(BaseModel):
    """One "10-A — Mathematics" card on the teacher's landing page."""

    grade_id: int
    grade_name: Optional[str] = None
    section_id: int
    section_name: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None

    #: `"10-A — Mathematics"`, pre-joined so both portals render one label
    #: without duplicating the concatenation logic.
    display_name: str

    upcoming_count: int = 0
    total_count: int = 0

    class Config:
        from_attributes = True


class SlipTestClassListResponse(BaseModel):
    total: int
    items: list[SlipTestClassCard]