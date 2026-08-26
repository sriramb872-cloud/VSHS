# app/crud/homework.py
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.homework import Homework
from app.schemas.homework import HomeworkCreate, HomeworkUpdate


class CRUDHomework:
    def get(self, db: Session, homework_id: int) -> Optional[Homework]:
        return db.query(Homework).filter(Homework.id == homework_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 20,
        school_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        section_ids: Optional[List[int]] = None,
        subject_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        due_date: Optional[date] = None
    ) -> Tuple[List[Homework], int]:
        query = db.query(Homework)

        if school_id is not None:
            query = query.filter(Homework.school_id == school_id)
        if grade_id is not None:
            query = query.filter(Homework.grade_id == grade_id)
        if section_id is not None:
            query = query.filter(Homework.section_id == section_id)
        if section_ids is not None:
            query = query.filter(Homework.section_id.in_(section_ids))
        if subject_id is not None:
            query = query.filter(Homework.subject_id == subject_id)
        if teacher_id is not None:
            query = query.filter(Homework.teacher_id == teacher_id)
        if due_date is not None:
            query = query.filter(Homework.due_date == due_date)

        total = query.count()
        items = query.order_by(Homework.due_date.asc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, db: Session, *, obj_in: HomeworkCreate, teacher_id: int, school_id: int) -> Homework:
        db_obj = Homework(
            school_id=school_id,
            teacher_id=teacher_id,
            grade_id=obj_in.grade_id,
            section_id=obj_in.section_id,
            subject_id=obj_in.subject_id,
            title=obj_in.title,
            description=obj_in.description,
            due_date=obj_in.due_date,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Homework, obj_in: HomeworkUpdate) -> Homework:
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Homework:
        obj = db.query(Homework).get(id)
        db.delete(obj)
        db.commit()
        return obj


homework = CRUDHomework()