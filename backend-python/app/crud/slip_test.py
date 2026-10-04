# backend-python/app/crud/slip_test.py
"""Slip test CRUD.

Deliberately thin: every caller is the service layer, which owns authorization,
validation and the notification transaction. This module only builds queries.

Two deliberate differences from the older CRUD modules:

1. **No ``commit()`` in ``create`` / ``update``.** The feature requires the slip
   test row and its fan-out of notifications to land in ONE transaction ("if
   either fails, roll back both"), so the service performs the single
   ``commit()``.
2. **Every list query takes ``school_id``** and applies it unconditionally. A
   missing school context is never a legitimate "unfiltered" request here.
"""
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.slip_test import SlipTest


class CRUDSlipTest:
    # -- reads ---------------------------------------------------------------

    def get(self, db: Session, id_val: int) -> Optional[SlipTest]:
        return db.query(SlipTest).filter(SlipTest.id == id_val).first()

    def get_multi(
        self,
        db: Session,
        *,
        school_id: int,
        teacher_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SlipTest]:
        """Slip tests for one school, soonest first.

        ``date_from`` / ``date_to`` are inclusive and are the mechanism behind
        the student portal's ``upcoming`` / ``past`` split — the split is derived
        per request, so a test moves tabs by itself once its date passes.
        """
        query = self._filter(
            db,
            school_id=school_id,
            teacher_id=teacher_id,
            academic_year_id=academic_year_id,
            grade_id=grade_id,
            section_id=section_id,
            subject_id=subject_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        return (
            query.order_by(
                SlipTest.scheduled_date.asc(),
                SlipTest.start_time.asc(),
                SlipTest.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_multi(self, db: Session, **filters) -> int:
        return self._filter(db, **filters).count()

    def count_upcoming_by_slot(
        self,
        db: Session,
        *,
        school_id: int,
        academic_year_id: Optional[int],
        today: date,
        teacher_id: Optional[int] = None,
    ) -> List[Tuple[int, int, int, int]]:
        """``(grade_id, section_id, subject_id, count)`` for scheduled tests that
        have not happened yet.

        One grouped query feeds every card on the teacher landing page, instead
        of one count query per card.
        """
        query = db.query(
            SlipTest.grade_id,
            SlipTest.section_id,
            SlipTest.subject_id,
            func.count(SlipTest.id),
        ).filter(
            SlipTest.school_id == school_id,
            SlipTest.scheduled_date >= today,
            func.lower(SlipTest.status) == "scheduled",
        )
        if teacher_id is not None:
            query = query.filter(SlipTest.teacher_id == teacher_id)
        if academic_year_id is not None:
            query = query.filter(SlipTest.academic_year_id == academic_year_id)

        return [
            (row[0], row[1], row[2], row[3])
            for row in query.group_by(
                SlipTest.grade_id, SlipTest.section_id, SlipTest.subject_id
            ).all()
        ]

    def find_same_slot_on_date(
        self,
        db: Session,
        *,
        school_id: int,
        academic_year_id: int,
        grade_id: int,
        section_id: int,
        subject_id: int,
        scheduled_date: date,
        exclude_id: Optional[int] = None,
    ) -> Optional[SlipTest]:
        """Any other slip test already on that class + subject + date.

        Used only to raise a *warning*: two tests on one day is unusual but not
        forbidden, so the caller still creates the row.
        """
        query = db.query(SlipTest).filter(
            SlipTest.school_id == school_id,
            SlipTest.academic_year_id == academic_year_id,
            SlipTest.grade_id == grade_id,
            SlipTest.section_id == section_id,
            SlipTest.subject_id == subject_id,
            SlipTest.scheduled_date == scheduled_date,
            func.lower(SlipTest.status) != "cancelled",
        )
        if exclude_id is not None:
            query = query.filter(SlipTest.id != exclude_id)
        return query.first()

    # -- writes (the caller commits) ----------------------------------------

    def create(self, db: Session, **values) -> SlipTest:
        db_obj = SlipTest(**values)
        db.add(db_obj)
        db.flush()  # assigns the PK without ending the caller's transaction
        return db_obj

    def update(self, db: Session, *, db_obj: SlipTest, values: dict) -> SlipTest:
        for field, value in values.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.flush()
        return db_obj

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _filter(
        db: Session,
        *,
        school_id: int,
        teacher_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ):
        """Shared predicate for ``get_multi`` / ``count_multi`` so the page and
        its total can never describe different row sets."""
        query = db.query(SlipTest).filter(SlipTest.school_id == school_id)
        if teacher_id is not None:
            query = query.filter(SlipTest.teacher_id == teacher_id)
        if academic_year_id is not None:
            query = query.filter(SlipTest.academic_year_id == academic_year_id)
        if grade_id is not None:
            query = query.filter(SlipTest.grade_id == grade_id)
        if section_id is not None:
            query = query.filter(SlipTest.section_id == section_id)
        if subject_id is not None:
            query = query.filter(SlipTest.subject_id == subject_id)
        if status:
            # ``status`` is a MySQL ENUM; compare case-insensitively so a caller
            # sending "CANCELLED" still matches the stored 'cancelled'.
            query = query.filter(func.lower(SlipTest.status) == status.lower())
        if date_from is not None:
            query = query.filter(SlipTest.scheduled_date >= date_from)
        if date_to is not None:
            query = query.filter(SlipTest.scheduled_date <= date_to)
        return query


crud_slip_test = CRUDSlipTest()