"""
SCHOLARIS ERP - Teacher Subject CRUD
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.teacher_subject import TeacherSubject
from app.schemas.teacher_subject import TeacherSubjectCreate, TeacherSubjectUpdate


class CRUDTeacherSubject:
    def get(self, db: Session, id_val: int) -> Optional[TeacherSubject]:
        return db.query(TeacherSubject).filter(TeacherSubject.id == id_val).first()

    def get_by_assignment(
        self, db: Session, teacher_id: int, subject_id: int, grade_id: int, section_id: int, school_id: int
    ) -> Optional[TeacherSubject]:
        return db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == teacher_id,
            TeacherSubject.subject_id == subject_id,
            TeacherSubject.grade_id == grade_id,
            TeacherSubject.section_id == section_id,
            TeacherSubject.school_id == school_id
        ).first()

    def get_multi_by_teacher(
        self, db: Session, teacher_id: int, school_id: Optional[int] = None
    ) -> List[TeacherSubject]:
        query = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id)
        if school_id:
            query = query.filter(TeacherSubject.school_id == school_id)
        return query.all()

    def get_multi_by_school(
        self, db: Session, school_id: int, skip: int = 0, limit: int = 100
    ) -> List[TeacherSubject]:
        return db.query(TeacherSubject).filter(
            TeacherSubject.school_id == school_id
        ).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TeacherSubjectCreate) -> TeacherSubject:
        db_obj = TeacherSubject(
            teacher_id=obj_in.teacher_id,
            subject_id=obj_in.subject_id,
            grade_id=obj_in.grade_id,
            section_id=obj_in.section_id,
            school_id=obj_in.school_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: TeacherSubject, obj_in: TeacherSubjectUpdate) -> TeacherSubject:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id_val: int) -> Optional[TeacherSubject]:
        obj = db.query(TeacherSubject).filter(TeacherSubject.id == id_val).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


crud_teacher_subject = CRUDTeacherSubject()
