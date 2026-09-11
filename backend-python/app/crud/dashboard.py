from typing import Optional
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.student_enrollment import StudentEnrollment


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
