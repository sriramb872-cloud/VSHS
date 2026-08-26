from typing import Optional
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.teacher import Teacher


class CRUDDashboard:
    def get_super_admin_stats(self, db: Session) -> dict:
        try:
            total_teachers = db.query(Teacher).count()
        except Exception:
            total_teachers = 0

        try:
            total_students = db.query(Student).count()
        except Exception:
            total_students = 0

        return {
            "total_schools": 1,
            "total_principals": 1,
            "total_teachers": total_teachers,
            "total_students": total_students,
            "active_schools": 1,
        }

    def get_principal_stats(self, db: Session, school_id: Optional[int]) -> dict:
        try:
            if school_id:
                total_teachers = db.query(Teacher).filter(Teacher.school_id == school_id).count()
            else:
                total_teachers = db.query(Teacher).count()
        except Exception:
            total_teachers = 0

        try:
            if school_id:
                total_students = db.query(Student).filter(Student.school_id == school_id).count()
            else:
                total_students = db.query(Student).count()
        except Exception:
            total_students = 0

        return {
            "total_teachers": total_teachers,
            "total_students": total_students,
            "todays_attendance": {
                "present": 0,
                "absent": 0,
                "total": 0,
            },
            "upcoming_exams": [],
            "announcements": [],
            "recent_homework": [],
            "calendar_events": [],
        }


dashboard = CRUDDashboard()
