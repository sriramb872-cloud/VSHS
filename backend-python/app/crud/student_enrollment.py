# backend-python/app/crud/student_enrollment.py
from typing import Dict, List, Optional, Tuple
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session
from app.models import StudentEnrollment, Student, Section


def get_student_enrollment(db: Session, enrollment_id: int) -> Optional[StudentEnrollment]:
    return db.query(StudentEnrollment).filter(StudentEnrollment.id == enrollment_id).first()


def get_student_enrollment_by_academic_year(db: Session, student_id: int, academic_year_id: int) -> Optional[StudentEnrollment]:
    return db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.academic_year_id == academic_year_id
    ).first()


def _get_attendance_percentages(db: Session, student_ids: List[int]) -> Dict[int, float]:
    """
    Calculate attendance percentage for the given student IDs using the
    actual database tables: attendance_records.

    attendance_records.status == 'PRESENT' counts as present.
    Returns a dict mapping student_id -> attendance percentage (0-100).
    """
    if not student_ids:
        return {}

    result = db.execute(
        text(
            "SELECT ar.student_id, "
            "       COUNT(*) AS total, "
            "       SUM(CASE WHEN ar.status = 'PRESENT' THEN 1 ELSE 0 END) AS present_count "
            "FROM attendance_records ar "
            "WHERE ar.student_id IN :student_ids "
            "GROUP BY ar.student_id"
        ).bindparams(bindparam("student_ids", expanding=True)),
        {"student_ids": student_ids},
    )

    pct_map: Dict[int, float] = {}
    for row in result:
        total = row[1]
        present = row[2]
        if total > 0:
            pct_map[row[0]] = round((present / total) * 100, 1)
    return pct_map


def get_enrollments(
    db: Session,
    school_id: Optional[int] = None,
    academic_year_id: Optional[int] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[StudentEnrollment], Dict[int, float]]:
    query = db.query(StudentEnrollment)

    if school_id:
        query = query.join(StudentEnrollment.student).filter(Student.school_id == school_id)

    if academic_year_id:
        query = query.filter(StudentEnrollment.academic_year_id == academic_year_id)

    if section_id:
        query = query.filter(StudentEnrollment.section_id == section_id)
    elif grade_id:
        query = query.join(StudentEnrollment.section).filter(Section.grade_id == grade_id)

    enrollments = query.offset(skip).limit(limit).all()

    # Collect unique student IDs and bulk-fetch attendance percentages
    student_ids = list({e.student_id for e in enrollments if e.student_id})
    attendance_map = _get_attendance_percentages(db, student_ids)

    return enrollments, attendance_map


def create_student_enrollment(db: Session, data: dict) -> StudentEnrollment:
    allowed_fields = {"student_id", "academic_year_id", "section_id", "roll_number"}
    clean_data = {k: v for k, v in data.items() if k in allowed_fields}
    db_item = StudentEnrollment(**clean_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_student_enrollment(db: Session, db_item: StudentEnrollment, data: dict) -> StudentEnrollment:
    allowed_fields = {"student_id", "academic_year_id", "section_id", "roll_number"}
    for key, value in data.items():
        if key in allowed_fields and hasattr(db_item, key):
            setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_student_enrollment(db: Session, db_item: StudentEnrollment) -> StudentEnrollment:
    db.delete(db_item)
    db.commit()
    return db_item
