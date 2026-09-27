"""Ad-hoc verification of attendance remarks persistence (QA only)."""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal  # noqa: E402
from app.models.attendance import Attendance  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        rows = (
            db.query(Attendance)
            .order_by(Attendance.date.desc(), Attendance.student_id)
            .all()
        )
        print(f"attendance_records rows: {len(rows)}")
        for r in rows:
            print(
                f"  id={r.id} student={r.student_id} section={r.section_id} "
                f"date={r.date} status={r.status} remarks={r.remarks!r}"
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
