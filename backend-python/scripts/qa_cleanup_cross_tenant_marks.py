"""QA cleanup: remove marks rows written across the school boundary.

During QA a principal of school 7 successfully POSTed marks into school 6's
exam before the tenant check in `MarksService._check_submission_permission` was
extended to cover principals. That left rows whose `entered_by_id` belongs to a
different school than the exam. This deletes exactly those rows inside the QA
schools and leaves every legitimate mark untouched.

Scoping note: an earlier version of this script computed the QA school ids,
refused to run without them, and then never used them - the delete loop walked
*every* `exam_subjects` row platform-wide. The guard was therefore decorative
and the script could delete a legitimate mark anywhere on the platform. It is
now filtered to the QA schools, which is what the guard always implied.

Usage
-----
    python scripts/qa_cleanup_cross_tenant_marks.py           # asks first
    python scripts/qa_cleanup_cross_tenant_marks.py --yes     # unattended
"""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.marks import Marks
from app.models.school import School
from app.models.user import User

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
        qa_school_ids = {
            row[0]
            for row in db.query(School.id).filter(School.name.like(f"{QA_PREFIX}%")).all()
        }
        if not qa_school_ids:
            print("No QA school found - refusing to touch the database.")
            return 1

        targets: list[tuple[int, int, int, int | None]] = []  # mark_id, exam_id, exam_school, actor_school
        for es in db.query(ExamSubject).all():
            exam = db.query(Exam).filter(Exam.id == es.exam_id).first()
            if not exam or exam.school_id not in qa_school_ids:
                continue  # QA schools only - see the scoping note in the docstring
            for mark in db.query(Marks).filter(Marks.exam_subject_id == es.id).all():
                actor_school = (
                    db.query(User.school_id).filter(User.id == mark.entered_by_id).scalar()
                )
                if actor_school is not None and actor_school != exam.school_id:
                    targets.append((mark.id, exam.id, exam.school_id, actor_school))

        if not targets:
            print("No cross-tenant mark rows found in the QA schools. Nothing to do.")
            return 0

        print("About to delete:")
        for mark_id, exam_id, exam_school, actor_school in targets:
            print(
                f"  marks id={mark_id} exam={exam_id} (school {exam_school}) "
                f"entered_by school {actor_school}"
            )
        if not _confirmed("This deletes QA data only."):
            print("Aborted.")
            return 1

        for mark_id, *_rest in targets:
            mark = db.query(Marks).filter(Marks.id == mark_id).first()
            if mark:
                db.delete(mark)
        db.commit()
        print(f"Removed {len(targets)} cross-tenant mark row(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
