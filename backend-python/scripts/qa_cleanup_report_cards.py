"""QA cleanup: remove report-card rows created by the cross-school test.

`POST /report-cards/generate` was reachable across schools during QA, which
regenerated QA school A's cards with `exam_id = NULL` and created a second set
of rows alongside the legitimate FA1 cards. This removes only rows for the two
QA schools that have a NULL exam_id, i.e. exactly the rows that attack
produced. Real (exam-scoped) report cards are left untouched.
Usage
-----
    python scripts/qa_cleanup_report_cards.py           # asks first
    python scripts/qa_cleanup_report_cards.py --yes     # unattended
"""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.report_card import ReportCard
from app.models.school import School
from app.models.student import Student

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
            row[0] for row in db.query(School.id).filter(School.name.like(f"{QA_PREFIX}%")).all()
        ]
        if not qa_school_ids:
            print("No QA school found - refusing to touch the database.")
            return 1

        qa_student_ids = {
            row[0]
            for row in db.query(Student.id).filter(Student.school_id.in_(qa_school_ids)).all()
        }

        targets = [
            r.id
            for r in db.query(ReportCard).all()
            if r.student_id in qa_student_ids and r.exam_id is None
        ]
        if not targets:
            print("No attack-created report card rows found. Nothing to do.")
            return 0

        print(f"About to delete {len(targets)} report card row(s) with exam_id = NULL:")
        for report_id in targets:
            print(f"  report_card id={report_id}")
        if not _confirmed("This deletes QA data only."):
            print("Aborted.")
            return 1

        for report_id in targets:
            report = db.query(ReportCard).filter(ReportCard.id == report_id).first()
            if report:
                db.delete(report)
        db.commit()
        print(f"Removed {len(targets)} attack-created report card row(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
