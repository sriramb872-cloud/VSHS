# backend-python/app/services/auth_service.py
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.core.security import verify_password, create_access_token


def authenticate_user(db: Session, mobile: str, password: str) -> Optional[User]:
    identifier = str(mobile).strip()
    
    # 1. Check direct mobile match
    users = db.query(User).filter(User.mobile == identifier).all()
    
    # 2. Check email match
    if not users:
        users = db.query(User).filter(User.email == identifier).all()
        
    # 3. Check Student ID / admission_number match (e.g. SCH2026001)
    if not users:
        student = db.query(Student).filter(Student.admission_number == identifier).first()
        if student and student.user:
            users = [student.user]
            
    # 4. Check Teacher Employee ID match (e.g. EMP2026001)
    if not users:
        teacher = db.query(Teacher).filter(Teacher.employee_id == identifier).first()
        if teacher and teacher.user:
            users = [teacher.user]

    if not users:
        return None

    for user in users:
        account_status = getattr(user, "is_active", "ACTIVE")
        if account_status != "ACTIVE":
            continue
        if verify_password(password, user.password_hash):
            return user
    return None


def create_user_token(user: User) -> str:
    access_token_data = {
        "sub": str(user.id),
        "role": user.role,
        "school_id": user.school_id
    }
    return create_access_token(data=access_token_data)