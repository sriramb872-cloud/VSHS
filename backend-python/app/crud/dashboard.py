from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.student_enrollment import StudentEnrollment


class CRUDDashboard:
    def get_super_admin_stats(self, db: Session) -> dict:
        """Platform-wide counts for the Super Admin dashboard / analytics.

        The school and principal counts used to be hard-coded to 1, so the
        dashboard and analytics pages reported a single school no matter how
        many were actually onboarded. Everything is now counted from the
        database.

        No broad ``except Exception: return 0`` wrappers here on purpose: they
        silently turn a coding mistake (e.g. referencing a non-existent
        attribute) into a plausible-looking zero, which is exactly how the
        hard-coded placeholders went unnoticed. If a table really is missing,
        ``create_all`` should have created it and a 500 with a traceback is the
        honest outcome.
        """
        from app.models.school import School
        from app.models.user import User

        return {
            "total_schools": db.query(func.count(School.id)).scalar() or 0,
            "active_schools": db.query(func.count(School.id))
            .filter(School.is_active.is_(True))
            .scalar()
            or 0,
            "total_principals": db.query(func.count(User.id))
            .filter(User.role == "PRINCIPAL")
            .scalar()
            or 0,
            "total_teachers": db.query(func.count(Teacher.id)).scalar() or 0,
            "total_students": db.query(func.count(Student.id)).scalar() or 0,
        }

    def get_principal_stats(self, db: Session, school_id: Optional[int], academic_year_id: Optional[int] = None) -> dict:
        try:
            if school_id:
                total_teachers = db.query(Teacher).filter(Teacher.school_id == school_id).count()
            else:
                total_teachers = db.query(Teacher).count()
        except Exception:
            total_teachers = 0

        try:
            if school_id:
                enrollment_query = db.query(StudentEnrollment).join(
                    Student, StudentEnrollment.student_id == Student.id
                ).filter(Student.school_id == school_id)
                if academic_year_id:
                    enrollment_query = enrollment_query.filter(StudentEnrollment.academic_year_id == academic_year_id)
                total_students = enrollment_query.count()
            else:
                total_students = db.query(StudentEnrollment).count()
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
