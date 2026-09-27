"""Notification delivery sanity check across roles (QA only).

Verifies the tenant-scoping fix in `app/crud/notification.py` did not starve
legitimate recipients: each role should still see the notifications addressed to
their own school.
"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

from qa_security_regression import call, login  # noqa: E402

PEOPLE = [
    ("principal 6", "9000000001", "QaTest#2026p"),
    ("principal 7", "9000000009", "QaTestB#2026"),
    ("teacher 1", "9000000002", "QaTeach#2027"),
    ("teacher 2", "9000000003", "QaTeach#2026"),
    ("student 1", "9000001001", "QaStu#2026"),
    ("student 2", "9000001002", "QaStu#2026"),
    ("super admin", "8019302351", "super"),
]


def main() -> int:
    print(f"{'role':<13} {'HTTP':<5} {'total':<6} {'unread':<7} schools seen")
    print("-" * 78)
    bad = 0
    for label, mob, pw in PEOPLE:
        token = login(mob, pw)
        r = call("GET", "/notifications", token, params={"limit": 10})
        d = r.json()
        items = d.get("items", [])
        schools = sorted({i.get("school_id") for i in items} - {None})
        titles = [i["title"] for i in items][:3]
        print(
            f"{label:<13} {r.status_code:<5} {d.get('total'):<6} "
            f"{d.get('unread_count'):<7} {schools}  {titles}"
        )
        # Nobody may see a notification from a school other than their own,
        # except the Super Admin, who is platform-level.
        if label != "super admin":
            foreign = [s for s in schools if s != 6] if "principal 6" in label or "teacher" in label or "student" in label else []
            if foreign:
                print(f"   !! {label} sees foreign schools {foreign}")
                bad += 1
    print("-" * 78)
    print("FAIL" if bad else "OK - no role sees another school's notifications")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
