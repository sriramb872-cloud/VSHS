"""
SCHOLARIS ERP - Teacher Subject Service
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.teacher_subject import TeacherSubjectRepository
from app.schemas.teacher_subject import TeacherSubjectCreate, TeacherSubjectUpdate, TeacherSubjectResponse


class TeacherSubjectService:
    def __init__(self, db: Session):
        self.repo = TeacherSubjectRepository(db)
        self.db = db

    def get_by_id(self, id_val: int) -> TeacherSubjectResponse:
        obj = self.repo.get_by_id(id_val)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
        return TeacherSubjectResponse.model_validate(obj)

    def get_by_teacher(
        self,
        teacher_id: int,
        school_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> List[TeacherSubjectResponse]:
        items = self.repo.get_by_teacher(teacher_id, school_id, academic_year_id=academic_year_id)
        return [TeacherSubjectResponse.model_validate(i) for i in items]

    def get_by_school(
        self,
        school_id: int,
        skip: int = 0,
        limit: int = 100,
        academic_year_id: Optional[int] = None,
    ) -> List[TeacherSubjectResponse]:
        items = self.repo.get_by_school(
            school_id, skip, limit, academic_year_id=academic_year_id
        )
        return [TeacherSubjectResponse.model_validate(i) for i in items]

    def _existing_for_slot(
        self,
        school_id: int,
        grade_id: int,
        section_id: int,
        subject_id: int,
        academic_year_id: Optional[int],
        teacher_id: Optional[int] = None,
        exclude_id: Optional[int] = None,
    ):
        """Any row already owning this subject/section/year combination."""
        from app.models.teacher_subject import TeacherSubject

        query = self.db.query(TeacherSubject).filter(
            TeacherSubject.school_id == school_id,
            TeacherSubject.grade_id == grade_id,
            TeacherSubject.section_id == section_id,
            TeacherSubject.subject_id == subject_id,
        )
        if teacher_id is not None:
            query = query.filter(TeacherSubject.teacher_id == teacher_id)
        if academic_year_id is None:
            # A year-less (legacy) row is matched by an exact NULL so we do
            # not treat every historical row as conflicting with a new one.
            query = query.filter(TeacherSubject.academic_year_id.is_(None))
        else:
            query = query.filter(
                (TeacherSubject.academic_year_id == academic_year_id)
                | (TeacherSubject.academic_year_id.is_(None))
            )
        if exclude_id is not None:
            query = query.filter(TeacherSubject.id != exclude_id)
        return query.first()

    def assign_teacher(self, obj_in: TeacherSubjectCreate) -> TeacherSubjectResponse:
        academic_year_id = getattr(obj_in, "academic_year_id", None)

        # Same teacher, same slot, same year -> nothing to do.
        same_teacher = self._existing_for_slot(
            obj_in.school_id,
            obj_in.grade_id,
            obj_in.section_id,
            obj_in.subject_id,
            academic_year_id,
            teacher_id=obj_in.teacher_id,
        )
        if same_teacher is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teacher is already assigned to this subject/grade/section",
            )

        # One teacher teaches a subject in a section per academic year. Two
        # different teachers for the same slot in the same year is rejected
        # here (the DB unique index enforces the same rule as a backstop).
        other_teacher = self._existing_for_slot(
            obj_in.school_id,
            obj_in.grade_id,
            obj_in.section_id,
            obj_in.subject_id,
            academic_year_id,
        )
        if other_teacher is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Another teacher is already assigned to this "
                    "subject/grade/section for the selected academic year"
                ),
            )

        obj = self.repo.create(obj_in)
        return TeacherSubjectResponse.model_validate(obj)

    def update_assignment(self, id_val: int, obj_in: TeacherSubjectUpdate) -> TeacherSubjectResponse:
        obj = self.repo.get_by_id(id_val)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
        data = obj_in.model_dump(exclude_unset=True)
        target_year = data.get("academic_year_id", obj.academic_year_id)
        conflicting = self._existing_for_slot(
            obj.school_id,
            data.get("grade_id", obj.grade_id),
            data.get("section_id", obj.section_id),
            data.get("subject_id", obj.subject_id),
            target_year,
            exclude_id=obj.id,
        )
        if conflicting is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Another teacher is already assigned to this "
                    "subject/grade/section for the selected academic year"
                ),
            )
        updated = self.repo.update(obj, obj_in)
        return TeacherSubjectResponse.model_validate(updated)

    def delete_assignment(self, id_val: int) -> None:
        obj = self.repo.get_by_id(id_val)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
        self.repo.delete(id_val)
