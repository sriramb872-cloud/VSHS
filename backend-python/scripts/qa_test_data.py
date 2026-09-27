"""QA test-data inventory and cleanup for the SCHOLARIS repository.

Everything this run created is prefixed `QA_` / `QA0` / `qa.` and lives inside
the two schools named `QA_AUTOTEST_*`. Those two schools are created *only* by
this QA exercise, so removing them (and only them) is safe and cascades to
their users, teachers, students, sections, grades, subjects, timetables,
enrollments, exams, marks, attendance, homework, announcements, notifications,
report cards and audit rows via the schema's ON DELETE rules.

Usage
-----
    python scripts/qa_test_data.py inventory     # list what QA created (read-only)
    python scripts/qa_test_data.py cleanup       # delete the QA schools (asks first)
    python scripts/qa_test_data.py cleanup --yes # unattended

`inventory` is the default action and is read-only. `cleanup` refuses to run
unless it finds at least one school whose name starts with `QA_AUTOTEST_`, it
prints what it is about to remove, and it asks for confirmation.
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import inspect, text

from app.core.database import SessionLocal, engine
from app.models.academic_year import AcademicYear
from app.models.announcement import Announcement
from app.models.attendance import Attendance
from app.models.calendar_event import CalendarEvent
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.grade import Grade
from app.models.homework import Homework
from app.models.marks import Marks
from app.models.notification import Notification
from app.models.report_card import ReportCard
from app.models.school import School
from app.models.section import Section
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.timetable import Timetable
from app.models.user import User

QA_SCHOOL_PREFIX = "QA_AUTOTEST_"


def qa_school_ids(db) -> list[int]:
    return [
        row[0]
        for row in db.query(School.id)
        .filter(School.name.like(f"{QA_SCHOOL_PREFIX}%"))
        .all()
    ]


def inventory(db) -> int:
    ids = qa_school_ids(db)
    if not ids:
        print("No QA_AUTOTEST_* schools found - nothing to report.")
        return 0

    print("QA schools:")
    for school in db.query(School).filter(School.id.in_(ids)).all():
        print(f"  #{school.id} {school.name} (code={school.code})")

    print("\nQA objects (id -> label):")
    rows = []

    def add(label, query, fmt):
        for obj in query.all():
            rows.append((label, obj.id, fmt(obj)))

    add("user", db.query(User).filter(User.school_id.in_(ids)), lambda u: f"{u.display_name} / {u.mobile} / {u.role}")
    add("teacher", db.query(Teacher).filter(Teacher.school_id.in_(ids)), lambda t: f"{t.user.display_name if t.user else '?'} ({t.employee_id})")
    add("student", db.query(Student).filter(Student.school_id.in_(ids)), lambda s: f"{s.user.display_name if s.user else '?'} ({s.admission_number})")
    add("grade", db.query(Grade).filter(Grade.school_id.in_(ids)), lambda g: g.name)
    add("section", db.query(Section).filter(Section.school_id.in_(ids)), lambda s: f"{s.name} (grade {s.grade_id})")
    add("subject", db.query(Subject).filter(Subject.school_id.in_(ids)), lambda s: s.name)
    add("academic_year", db.query(AcademicYear).filter(AcademicYear.school_id.in_(ids)), lambda a: a.name)
    add("enrollment", db.query(StudentEnrollment).join(Student).filter(Student.school_id.in_(ids)), lambda e: f"student {e.student_id} -> section {e.section_id}, roll {e.roll_number}")
    add("timetable", db.query(Timetable).filter(Timetable.school_id.in_(ids)), lambda t: f"section {t.section_id} subject {t.subject_id} {t.day_of_week} {t.start_time}")
    add("exam", db.query(Exam).filter(Exam.school_id.in_(ids)), lambda e: f"{e.name} section {e.section_id} status {e.status}")
    add("exam_subject", db.query(ExamSubject).join(Exam).filter(Exam.school_id.in_(ids)), lambda e: f"exam {e.exam_id} subject {e.subject_id} submitted={e.is_marks_submitted}")
    add("marks", db.query(Marks).filter(Marks.school_id.in_(ids)), lambda m: f"exam_subject {m.exam_subject_id} student {m.student_id} = {m.marks_obtained}")
    add("attendance", db.query(Attendance).join(Section).filter(Section.school_id.in_(ids)), lambda a: f"student {a.student_id} {a.date} {a.status}")
    add("homework", db.query(Homework).filter(Homework.school_id.in_(ids)), lambda h: f"{h.title} section {h.section_id}")
    add("announcement", db.query(Announcement).filter(Announcement.school_id.in_(ids)), lambda a: f"{a.title} [{a.status}]")
    add("calendar_event", db.query(CalendarEvent).filter(CalendarEvent.school_id.in_(ids)), lambda c: f"{c.title} {c.start_date}")
    add("notification", db.query(Notification).filter(Notification.school_id.in_(ids)), lambda n: f"{n.title} ({n.category})")
    add("report_card", db.query(ReportCard).join(Student).filter(Student.school_id.in_(ids)), lambda r: f"student {r.student_id} year {r.academic_year_id} exam {r.exam_id} total {r.total_marks}")

    for label, obj_id, text_value in rows:
        print(f"  {label:<16} #{obj_id:<5} {text_value}")

    print(f"\nTotal QA objects: {len(rows)}")
    print(f"Run `python scripts/qa_test_data.py cleanup` to delete the {len(ids)} QA school(s)")
    print("and everything that cascades from them. Non-QA schools are never touched.")
    return 0


def cleanup(db) -> int:
    ids = qa_school_ids(db)
    if not ids:
        print("No QA_AUTOTEST_* schools found - refusing to delete anything.")
        return 1

    schools = db.query(School).filter(School.id.in_(ids)).all()
    print("About to delete:")
    for school in schools:
        print(f"  school #{school.id} {school.name} (code={school.code})")

    if "--yes" not in sys.argv and "-y" not in sys.argv:
        try:
            answer = input("Type 'yes' to delete the QA schools and everything under them: ")
        except EOFError:
            answer = ""
        if answer.strip().lower() != "yes":
            print("Aborted - nothing was deleted.")
            return 1

    # Delete in an order that avoids relying on ON DELETE rules that may not be
    # present on an older schema, and so the exam/report-card chain goes first.
    for label, query in [
        ("report_card", db.query(ReportCard).join(Student).filter(Student.school_id.in_(ids))),
        ("notification", db.query(Notification).filter(Notification.school_id.in_(ids))),
        ("calendar_event", db.query(CalendarEvent).filter(CalendarEvent.school_id.in_(ids))),
        ("announcement", db.query(Announcement).filter(Announcement.school_id.in_(ids))),
        ("homework", db.query(Homework).filter(Homework.school_id.in_(ids))),
        ("marks", db.query(Marks).filter(Marks.school_id.in_(ids))),
    ]:
        for obj in query.all():
            db.delete(obj)
    db.commit()

    for exam in db.query(Exam).filter(Exam.school_id.in_(ids)).all():
        db.delete(exam)
    db.commit()

    for att in db.query(Attendance).join(Section).filter(Section.school_id.in_(ids)).all():
        db.delete(att)
    db.commit()

    for tt in db.query(Timetable).filter(Timetable.school_id.in_(ids)).all():
        db.delete(tt)
    db.commit()

    for enr in db.query(StudentEnrollment).join(Student).filter(Student.school_id.in_(ids)).all():
        db.delete(enr)
    db.commit()

    for school_id in ids:
        for teacher in db.query(Teacher).filter(Teacher.school_id == school_id).all():
            db.delete(teacher)
        for student in db.query(Student).filter(Student.school_id == school_id).all():
            db.delete(student)
        for section in db.query(Section).filter(Section.school_id == school_id).all():
            db.delete(section)
        for grade in db.query(Grade).filter(Grade.school_id == school_id).all():
            db.delete(grade)
        for subject in db.query(Subject).filter(Subject.school_id == school_id).all():
            db.delete(subject)
        for year in db.query(AcademicYear).filter(AcademicYear.school_id == school_id).all():
            db.delete(year)
        for user in db.query(User).filter(User.school_id == school_id).all():
            db.delete(user)
        db.delete(db.query(School).filter(School.id == school_id).first())
    db.commit()

    remaining = db.query(School).filter(School.id.in_(ids)).count()
    print(f"Cleanup complete. QA schools remaining: {remaining}")
    print("Non-QA schools were not touched.")
    return 0


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    db = SessionLocal()
    try:
        if action == "inventory":
            return inventory(db)
        if action == "cleanup":
            return cleanup(db)
        print(__doc__)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
