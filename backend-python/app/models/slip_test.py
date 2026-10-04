# backend-python/app/models/slip_test.py
"""Slip test model — a short, low-stakes assessment scheduled by a subject
teacher for one class + section + subject inside one academic year.

Scope note
----------
This table stores the *test*, not its results. ``max_marks`` is the maximum /
total marks of the test. Recording what each student obtained is explicitly out
of scope; a future ``slip_test_results`` table will link to ``slip_tests.id``
(one row per student) and reuse ``max_marks`` as the denominator. Nothing here
blocks that: ``id`` is a stable surrogate primary key.

Conventions followed from the rest of the schema
-----------------------------------------------
* ``id`` is the plain primary key (same shape as ``homework``, ``exams``,
  ``teacher_subjects``).
* Every tenant-scoped column carries ``school_id`` so a query can always be
  scoped to one school (multi-school safety).
* ``scheduled_date`` is a ``DATE`` and ``start_time`` a ``TIME``: both are plain
  school-local values and are never shifted through UTC anywhere in the feature.
  The ``created_at`` / ``updated_at`` timestamps follow the project-wide naive
  UTC convention (``datetime.utcnow``), see ``app/core/time_utils.py``.
* ``status`` is an ``ENUM`` — the same shape ``users.role`` already uses in this
  codebase, so MySQL rejects an unknown lifecycle value at the storage layer.
  Values are lowercase (``scheduled`` / ``cancelled`` / ``completed``) and are
  normalised with ``func.lower`` on read so casing can never surprise a filter.
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


#: Allowed lifecycle values. Kept as a module constant so the schema, the
#: service and the tests can never drift apart.
SLIP_TEST_STATUSES = ("scheduled", "cancelled", "completed")

DEFAULT_SLIP_TEST_STATUS = "scheduled"


class SlipTest(Base):
    __tablename__ = "slip_tests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id = Column(
        Integer,
        ForeignKey("academic_years.academic_year_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Class structure is copied exactly as `homework` and `timetables` model it:
    # both a grade and a section, with the section belonging to that grade.
    grade_id = Column(
        Integer, ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id = Column(
        Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True
    )

    subject_id = Column(
        Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: The teacher who created the test. Also the owner used for edit/cancel.
    teacher_id = Column(
        Integer, ForeignKey("teachers.teacher_id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(150), nullable=False)
    #: Syllabus / topics. Nullable and capped at 1000 characters by the schema.
    description = Column(Text, nullable=True)

    scheduled_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    max_marks = Column(Integer, nullable=False)

    status = Column(
        Enum(*SLIP_TEST_STATUSES, name="slip_test_status"),
        default=DEFAULT_SLIP_TEST_STATUS,
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    school = relationship("School")
    academic_year = relationship("AcademicYear")
    grade = relationship("Grade")
    section = relationship("Section")
    subject = relationship("Subject")
    teacher = relationship("Teacher")

    __table_args__ = (
        # Powers the student class listing and the teacher's "count upcoming"
        # cards. Name is explicit rather than auto-generated because it is part
        # of the standalone SQL migration script.
        Index(
            "ix_slip_tests_school_year_class_date",
            "school_id",
            "academic_year_id",
            "grade_id",
            "section_id",
            "scheduled_date",
        ),
        Index("ix_slip_tests_teacher_date", "teacher_id", "scheduled_date"),
    )


SlipTestModel = SlipTest