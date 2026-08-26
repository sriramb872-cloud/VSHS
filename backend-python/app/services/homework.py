# app/services/homework.py
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.homework import homework as crud_homework
from app.schemas.homework import HomeworkCreate, HomeworkUpdate
from app.models.homework import Homework
from app.models.student import Student
from app.models.user import User


class HomeworkService:
    @staticmethod
    def get_homework(
        db: Session, homework_id: int, current_user: Optional[User] = None
    ) -> Optional[Homework]:
        db_obj = crud_homework.get(db, homework_id=homework_id)
        if not db_obj:
            return None

        if current_user:
            role = str(current_user.role).upper()
            if role != "SUPER_ADMIN":
                if db_obj.school_id != current_user.school_id:
                    return None

            if role == "STUDENT":
                student = getattr(current_user, "student_profile", None) or (
                    db.query(Student).filter(Student.user_id == current_user.id).first()
                )
                if not student or not student.enrollments:
                    return None
                student_section_ids = [e.section_id for e in student.enrollments]
                if db_obj.section_id not in student_section_ids:
                    return None

        return db_obj

    @staticmethod
    def list_homework(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        due_date: Optional[date] = None,
        current_user: Optional[User] = None,
    ) -> Tuple[List[Homework], int]:
        school_id = None
        section_ids = None

        if current_user:
            role = str(current_user.role).upper()
            if role != "SUPER_ADMIN":
                school_id = current_user.school_id

            if role == "TEACHER" and teacher_id is None:
                from app.models.teacher import Teacher
                teacher = getattr(current_user, "teacher_profile", None) or (
                    db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
                )
                if teacher:
                    teacher_id = teacher.id

            if role == "STUDENT":
                student = getattr(current_user, "student_profile", None) or (
                    db.query(Student).filter(Student.user_id == current_user.id).first()
                )
                if not student or not student.enrollments:
                    return [], 0
                section_ids = [e.section_id for e in student.enrollments]
                grade_id = None
                section_id = None

        return crud_homework.get_multi(
            db,
            skip=skip,
            limit=limit,
            school_id=school_id,
            academic_year_id=academic_year_id,
            grade_id=grade_id,
            section_id=section_id,
            section_ids=section_ids,
            subject_id=subject_id,
            teacher_id=teacher_id,
            due_date=due_date,
        )

    @staticmethod
    def create_homework(
        db: Session, obj_in: HomeworkCreate, teacher_id: int, school_id: int
    ) -> Homework:
        return crud_homework.create(db, obj_in=obj_in, teacher_id=teacher_id, school_id=school_id)

    @staticmethod
    def update_homework(
        db: Session,
        homework_id: int,
        obj_in: HomeworkUpdate,
        teacher_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> Optional[Homework]:
        db_obj = crud_homework.get(db, homework_id=homework_id)
        if not db_obj:
            return None
        if school_id is not None and db_obj.school_id != school_id:
            return None
        if teacher_id is not None and db_obj.teacher_id != teacher_id:
            return None
        return crud_homework.update(db, db_obj=db_obj, obj_in=obj_in)

    @staticmethod
    def delete_homework(
        db: Session,
        homework_id: int,
        teacher_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> bool:
        db_obj = crud_homework.get(db, homework_id=homework_id)
        if not db_obj:
            return False
        if school_id is not None and db_obj.school_id != school_id:
            return False
        if teacher_id is not None and db_obj.teacher_id != teacher_id:
            return False
        crud_homework.remove(db, id=homework_id)
        return True