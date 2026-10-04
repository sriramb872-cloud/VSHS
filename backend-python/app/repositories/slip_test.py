# backend-python/app/repositories/slip_test.py
"""Slip test repository.

Mirrors ``TeacherSubjectRepository``: a thin, injected wrapper over
``crud_slip_test`` so the service depends on one object rather than importing
the CRUD module directly.
"""
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.crud.slip_test import crud_slip_test
from app.models.slip_test import SlipTest


class SlipTestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id_val: int) -> Optional[SlipTest]:
        return crud_slip_test.get(self.db, id_val)

    def list(
        self,
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
        return crud_slip_test.get_multi(
            self.db,
            school_id=school_id,
            teacher_id=teacher_id,
            academic_year_id=academic_year_id,
            grade_id=grade_id,
            section_id=section_id,
            subject_id=subject_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )

    def count(self, **filters) -> int:
        return crud_slip_test.count_multi(self.db, **filters)

    def upcoming_counts_by_slot(
        self,
        *,
        school_id: int,
        academic_year_id: Optional[int],
        today: date,
        teacher_id: Optional[int] = None,
    ) -> List[Tuple[int, int, int, int]]:
        return crud_slip_test.count_upcoming_by_slot(
            self.db,
            school_id=school_id,
            academic_year_id=academic_year_id,
            today=today,
            teacher_id=teacher_id,
        )

    def find_same_slot_on_date(self, **kwargs) -> Optional[SlipTest]:
        return crud_slip_test.find_same_slot_on_date(self.db, **kwargs)

    def create(self, **values) -> SlipTest:
        return crud_slip_test.create(self.db, **values)

    def update(self, db_obj: SlipTest, values: dict) -> SlipTest:
        """Apply ``values`` to an existing row. No commit — the caller owns the
        transaction so the row and its notifications land together."""
        return crud_slip_test.update(self.db, db_obj=db_obj, values=values)