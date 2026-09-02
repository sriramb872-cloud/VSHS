# backend-python/app/crud/teacher.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Teacher


def get_teacher(db: Session, teacher_id: int) -> Optional[Teacher]:
    return db.query(Teacher).filter(Teacher.id == teacher_id).first()


def get_teacher_by_user_id(db: Session, user_id: int) -> Optional[Teacher]:
    return db.query(Teacher).filter(Teacher.user_id == user_id).first()


def get_teachers_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Teacher]:
    return db.query(Teacher).filter(
        Teacher.school_id == school_id
    ).offset(skip).limit(limit).all()


def create_teacher(db: Session, school_id: int, user_id: int, data: dict) -> Teacher:
    teacher_fields = {"employee_id", "qualification", "department", "joining_date", "address"}
    clean_data = {k: v for k, v in data.items() if k in teacher_fields}
    if "specialization" in data and "department" not in clean_data:
        clean_data["department"] = data["specialization"]
    db_item = Teacher(school_id=school_id, user_id=user_id, **clean_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_teacher(db: Session, db_item: Teacher, data: dict) -> Teacher:
    teacher_fields = {"employee_id", "qualification", "department", "joining_date", "address"}
    for key, value in data.items():
        if key in teacher_fields and hasattr(db_item, key):
            setattr(db_item, key, value)
        elif key == "specialization" and hasattr(db_item, "department"):
            setattr(db_item, "department", value)

    if db_item.user:
        if "display_name" in data and data["display_name"] is not None:
            db_item.user.display_name = str(data["display_name"]).strip()
        elif "full_name" in data and data["full_name"] is not None:
            db_item.user.display_name = str(data["full_name"]).strip()
        if "email" in data and data["email"] is not None:
            db_item.user.email = data["email"]
        if "mobile" in data and data["mobile"] is not None:
            db_item.user.mobile = data["mobile"]
        if "profile_photo" in data and data["profile_photo"] is not None:
            db_item.user.profile_photo = data["profile_photo"]

    db.commit()
    db.refresh(db_item)
    return db_item


def delete_teacher(db: Session, db_item: Teacher) -> Teacher:
    db.delete(db_item)
    db.commit()
    return db_item

