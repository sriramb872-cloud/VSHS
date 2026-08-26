# backend-python/app/services/id_generator.py
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.principal import Principal


def generate_student_id(db: Session, school_id: int) -> str:
    """
    Generate unique Student ID in standard format: SCH{YEAR}{001...}
    Example: SCH2026001
    """
    current_year = datetime.utcnow().year
    prefix = f"SCH{current_year}"
    
    # Find all student admission numbers starting with prefix
    existing_students = (
        db.query(Student.admission_number)
        .filter(Student.admission_number.like(f"{prefix}%"))
        .all()
    )
    
    max_num = 0
    for (adm_num,) in existing_students:
        if adm_num and adm_num.startswith(prefix):
            suffix = adm_num[len(prefix):]
            if suffix.isdigit():
                num = int(suffix)
                if num > max_num:
                    max_num = num
                    
    next_num = max_num + 1
    return f"{prefix}{next_num:03d}"


def generate_employee_id(db: Session, school_id: int) -> str:
    """
    Generate unique Employee ID in standard format: EMP{YEAR}{001...}
    Example: EMP2026001
    """
    current_year = datetime.utcnow().year
    prefix = f"EMP{current_year}"
    
    existing_teachers = (
        db.query(Teacher.employee_id)
        .filter(Teacher.employee_id.like(f"{prefix}%"))
        .all()
    )
    
    max_num = 0
    for (emp_id,) in existing_teachers:
        if emp_id and emp_id.startswith(prefix):
            suffix = emp_id[len(prefix):]
            if suffix.isdigit():
                num = int(suffix)
                if num > max_num:
                    max_num = num
                    
    next_num = max_num + 1
    return f"{prefix}{next_num:03d}"


def generate_principal_id(db: Session, school_id: int) -> str:
    """
    Generate unique Principal Employee ID in standard format: PRN{YEAR}{001...}
    Example: PRN2026001
    """
    current_year = datetime.utcnow().year
    prefix = f"PRN{current_year}"

    existing_principals = (
        db.query(Principal.employee_id)
        .filter(Principal.employee_id.like(f"{prefix}%"))
        .all()
    )

    max_num = 0
    for (emp_id,) in existing_principals:
        if emp_id and emp_id.startswith(prefix):
            suffix = emp_id[len(prefix):]
            if suffix.isdigit():
                num = int(suffix)
                if num > max_num:
                    max_num = num

    next_num = max_num + 1
    return f"{prefix}{next_num:03d}"
