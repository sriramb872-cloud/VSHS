"""QA cleanup helper.

Deletes ONLY the marks row that the QA IDOR probe created for a student that is
not enrolled in the exam's section, and resets that exam subject back to
"marks not submitted" so the browser workflow can be retested from a clean
state. Scoped to the QA school (name prefix QA_AUTOTEST_) - it refuses to run
if the school does not look like QA data.
Usage
-----
    python scripts/qa_cleanup_marks.py           # asks first
    python scripts/qa_cleanup_marks.py --yes     # unattended
"""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.marks import Marks
from app.models.school import School
from app.models.student_enrollment import StudentEnrollment

QA_PREFIX = "QA_AUTOTEST_"


def _confirmed(prompt: str) -> bool:
    """Require an explicit yes unless --yes was passed."""
    if "--yes" in sys.argv or "-y" in sys.argv:
        return True
    try:
        answer = input(f"{prompt} Type 'yes' to continue: ")
    except EOFError:
        return False
    return answer.strip().lower() == "yes"


def main() -> int:
    db = SessionLocal()
    try:
        qa_school_ids = [
            row[0]
            for row in db.query(School.id)
            .filter(School.name.like(f"{QA_PREFIX}%"))
            .all()
        ]
        if not qa_school_ids:
            print("No QA school found - refusing to touch the database.")
            return 1
        print(f"QA school ids: {qa_school_ids}")

        stray_ids: list[int] = []
        for exam in db.query(Exam).filter(Exam.school_id.in_(qa_school_ids)).all():
            enrolled = {
                row[0]
                for row in db.query(StudentEnrollment.student_id)
                .filter(
                    StudentEnrollment.section_id == exam.section_id,
                    StudentEnrollment.academic_year_id == exam.academic_year_id,
                )
                .all()
            }
            for es in db.query(ExamSubject).filter(ExamSubject.exam_id == exam.id).all():
                for m in db.query(Marks).filter(Marks.exam_subject_id == es.id).all():
                    if m.student_id not in enrolled:
                        stray_ids.append(m.id)

        exams = db.query(Exam).filter(Exam.school_id.in_(qa_school_ids)).all()
        print(f"About to delete {len(stray_ids)} stray mark row(s) and reset the "
              f"submission flags of {len(exams)} QA exam(s).")
        for mark_id in stray_ids:
            print(f"  removing stray marks id={mark_id}")
        if not _confirmed("This changes QA data only."):
            print("Aborted.")
            return 1

        for mark_id in stray_ids:
            mark = db.query(Marks).filter(Marks.id == mark_id).first()
            if mark:
                db.delete(mark)
        db.commit()

        # Reset submission flags so the end-to-end workflow can run again.
        for exam in exams:
            for es in db.query(ExamSubject).filter(ExamSubject.exam_id == exam.id).all():
                es.is_marks_submitted = False
                es.submitted_at = None
            if exam.status == "MARKS_IN_PROGRESS":
                exam.status = "SCHEDULED"
        db.commit()
        print(f"Removed {len(stray_ids)} stray mark row(s); reset QA exam submission flags.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
