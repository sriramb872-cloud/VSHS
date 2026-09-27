"""Restore a user role that a QA probe changed by mistake (QA only).

The security regression script briefly flipped user id 2 (mobile 80193023251,
school 1) from PRINCIPAL to STUDENT while probing role assignment. This puts it
back. Idempotent: it only writes when the current role is not PRINCIPAL.
"""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402

TARGET_ID = 2
EXPECTED_ROLE = "PRINCIPAL"


def main() -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == TARGET_ID).first()
        if not user:
            print(f"user {TARGET_ID} not found - nothing to do")
            return 0
        current = str(getattr(user.role, "value", user.role))
        print(f"before: id={user.id} mobile={user.mobile} role={current} school_id={user.school_id}")
        if current == EXPECTED_ROLE:
            print("already correct - no change made")
            return 0
        user.role = EXPECTED_ROLE
        db.commit()
        db.refresh(user)
        after = str(getattr(user.role, "value", user.role))
        print(f"after:  id={user.id} mobile={user.mobile} role={after} school_id={user.school_id}")
        return 0 if after == EXPECTED_ROLE else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
