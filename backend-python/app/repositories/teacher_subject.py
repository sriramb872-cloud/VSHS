"""
SCHOLARIS ERP - Teacher Subject Assignment Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.teacher_subject import TeacherSubject
from app.crud.teacher_subject import crud_teacher_subject
from app.schemas.teacher_subject import TeacherSubjectCreate, TeacherSubjectUpdate


class TeacherSubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id_val: int) -> Optional[TeacherSubject]:
        return crud_teacher_subject.get(self.db, id_val)

    def get_by_teacher(self, teacher_id: int, school_id: Optional[int] = None) -> List[TeacherSubject]:
        return crud_teacher_subject.get_multi_by_teacher(self.db, teacher_id, school_id)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[TeacherSubject]:
        return crud_teacher_subject.get_multi_by_school(self.db, school_id, skip, limit)

    def create(self, obj_in: TeacherSubjectCreate) -> TeacherSubject:
        return crud_teacher_subject.create(self.db, obj_in)

    def update(self, db_obj: TeacherSubject, obj_in: TeacherSubjectUpdate) -> TeacherSubject:
        return crud_teacher_subject.update(self.db, db_obj, obj_in)

    def delete(self, id_val: int) -> Optional[TeacherSubject]:
        return crud_teacher_subject.delete(self.db, id_val)
