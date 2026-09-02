# backend-python/app/crud/student.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Student


def get_student(db: Session, student_id: int) -> Optional[Student]:
    return db.query(Student).filter(Student.id == student_id).first()


def get_student_by_user_id(db: Session, user_id: int) -> Optional[Student]:
    return db.query(Student).filter(Student.user_id == user_id).first()


def get_student_by_admission_number(db: Session, admission_number: str) -> Optional[Student]:
    return db.query(Student).filter(Student.admission_number == admission_number).first()


def get_students_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Student]:
    return db.query(Student).filter(
        Student.school_id == school_id
    ).offset(skip).limit(limit).all()


def create_student(db: Session, school_id: int, user_id: int, data: dict) -> Student:
    student_fields = {
        "admission_number", "roll_number", "admission_date", "date_of_birth",
        "gender", "blood_group", "father_name", "father_mobile",
        "mother_name", "mother_mobile", "guardian_mobile", "address", "student_status"
    }
    clean_data = {k: v for k, v in data.items() if k in student_fields}
    db_item = Student(school_id=school_id, user_id=user_id, **clean_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_student(db: Session, db_item: Student, data: dict) -> Student:
    from datetime import datetime, date

    student_fields = {
        "admission_number", "roll_number", "admission_date", "date_of_birth",
        "gender", "blood_group", "father_name", "father_mobile",
        "mother_name", "mother_mobile", "guardian_mobile", "address", "student_status"
    }
    for key, value in data.items():
        if key in student_fields and hasattr(db_item, key):
            if key in ["date_of_birth", "admission_date"] and isinstance(value, str):
                try:
                    if "T" in value:
                        value = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                    else:
                        value = date.fromisoformat(value[:10])
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid date format for {key}: {value}") from e
            setattr(db_item, key, value)

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


def delete_student(db: Session, db_item: Student) -> Student:
    db.delete(db_item)
    db.commit()
    return db_item

