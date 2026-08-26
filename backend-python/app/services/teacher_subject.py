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

    def get_by_id(self, id_val: int) -> TeacherSubjectResponse:
        obj = self.repo.get_by_id(id_val)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
        return TeacherSubjectResponse.model_validate(obj)

    def get_by_teacher(self, teacher_id: int, school_id: Optional[int] = None) -> List[TeacherSubjectResponse]:
        items = self.repo.get_by_teacher(teacher_id, school_id)
        return [TeacherSubjectResponse.model_validate(i) for i in items]

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[TeacherSubjectResponse]:
        items = self.repo.get_by_school(school_id, skip, limit)
        return [TeacherSubjectResponse.model_validate(i) for i in items]

    def assign_teacher(self, obj_in: TeacherSubjectCreate) -> TeacherSubjectResponse:
        existing = self.repo.get_by_teacher(obj_in.teacher_id, obj_in.school_id)
        for item in existing:
            if (
                item.subject_id == obj_in.subject_id
                and item.grade_id == obj_in.grade_id
                and item.section_id == obj_in.section_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Teacher is already assigned to this subject/grade/section"
                )
        obj = self.repo.create(obj_in)
        return TeacherSubjectResponse.model_validate(obj)

    def update_assignment(self, id_val: int, obj_in: TeacherSubjectUpdate) -> TeacherSubjectResponse:
        obj = self.repo.get_by_id(id_val)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
        updated = self.repo.update(obj, obj_in)
        return TeacherSubjectResponse.model_validate(updated)

    def delete_assignment(self, id_val: int) -> None:
        obj = self.repo.get_by_id(id_val)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found")
        self.repo.delete(id_val)
