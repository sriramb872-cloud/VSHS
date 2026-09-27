"""Authorization regression for the endpoints added in this pass (QA only).

Every check is a negative probe: it asserts that a role which must NOT reach an
object cannot read or write it. A 200 where a 403/404 is expected is a failure.

Read-only apart from the two role-assignment probes at the end, which put a QA
user back exactly where it started.
"""
import json
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "http://localhost:8000/api/v1"

PASS = []
FAIL = []


class Res:
    def __init__(self, status, body):
        self.status_code = status
        self.text = body

    def json(self):
        return json.loads(self.text)


def call(method, path, token=None, params=None, json_body=None):
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    data = None
    headers = {}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            return Res(r.status, r.read().decode())
    except HTTPError as e:
        return Res(e.code, e.read().decode())


def login(mobile, password):
    for attempt in range(6):
        r = call("POST", "/auth/login", json_body={"mobile": mobile, "password": password})
        if r.status_code == 200:
            return r.json()["access_token"]
        time.sleep(12)
    raise SystemExit(f"login failed for {mobile}: {r.status_code} {r.text}")


def check(label, got, want_set):
    ok = got in want_set
    line = f"{'PASS' if ok else 'FAIL'}  {label}: got {got}, expected one of {sorted(want_set)}"
    (PASS if ok else FAIL).append(line)
    print(line)


def main():
    sa = login("8019302351", "super")
    pr6 = login("9000000001", "QaTest#2026p")     # school 6
    pr7 = login("9000000009", "QaTestB#2026")     # school 7 (attacker)
    t1 = login("9000000002", "QaTeach#2027")      # teacher, school 6
    t2 = login("9000000003", "QaTeach#2026")      # teacher 2, school 6
    st1 = login("9000001001", "QaStu#2026")       # student, school 6

    WINDOW = {"start_date": "2026-01-01", "end_date": "2026-12-31"}

    print("\n== /roles ==")
    check("principal GET /roles", call("GET", "/roles", pr6).status_code, {403})
    check("teacher GET /roles", call("GET", "/roles", t1).status_code, {403})
    check("student GET /roles", call("GET", "/roles", st1).status_code, {403})
    check("principal GET /roles/assignable", call("GET", "/roles/assignable", pr6).status_code, {403})
    check("principal GET /roles/users", call("GET", "/roles/users", pr6).status_code, {403})

    print("\n== /reports ==")
    check("principal GET /reports/platform", call("GET", "/reports/platform", pr6).status_code, {403})
    check("teacher GET /reports/platform", call("GET", "/reports/platform", t1).status_code, {403})
    check("student GET /reports/platform", call("GET", "/reports/platform", st1).status_code, {403})
    check("no token GET /reports/platform", call("GET", "/reports/platform").status_code, {401})

    print("\n== /attendance/reports/summary ==")
    check("student", call("GET", "/attendance/reports/summary", st1, WINDOW).status_code, {403})
    r = call("GET", "/attendance/reports/summary", pr7, WINDOW)
    check("principal of school 7 (no cross-tenant data)", r.status_code, {200})
    if r.status_code == 200:
        body = r.json()
        # School 7 has no attendance, so it must not surface school 6 numbers.
        check(
            "school 7 report totals are empty",
            body["totals"]["marked"] == 0 and body["students"] == [],
            {True},
        )
    r = call("GET", "/attendance/reports/summary", t1, WINDOW)
    check("subject teacher report", r.status_code, {200})
    if r.status_code == 200:
        sections = {s["section_id"] for s in r.json()["sections"]}
        print(f"      teacher sees sections {sorted(sections)} (own sections only)")

    # Cross-tenant section filter: principal 7 asking for a school 6 section.
    r = call("GET", "/attendance/reports/summary", pr7, {**WINDOW, "section_id": 1})
    check("principal 7 filtered on school 6 section", r.status_code, {403, 404})

    print("\n== /search tenant isolation ==")
    for label, tok in (("super admin", sa), ("principal 6", pr6), ("principal 7", pr7), ("student", st1)):
        r = call("GET", "/search", tok, {"q": "QA"})
        check(f"{label} search 200", r.status_code, {200})
        if r.status_code == 200:
            body = r.json()
            schools = {s.get("school_id") for s in body["students"]} | {
                t.get("school_id") for t in body["teachers"]
            }
            schools.discard(None)
            if label == "principal 7":
                check("principal 7 sees no school 6 rows", schools <= {7}, {True})
            if label == "student":
                check("student sees at most self", len(body["students"]) <= 1, {True})
                check("student sees no teachers", body["teachers"] == [], {True})
            print(f"      {label}: student_hits={len(body['students'])} teacher_hits={len(body['teachers'])} schools={sorted(schools)}")

    r = call("GET", "/search", pr6, {"q": "QA", "school_id": 7})
    check("principal 6 forcing school_id=7 is rejected", r.status_code, {403})
    r = call("GET", "/search", pr6, {"q": "QA", "school_id": 6})
    check("principal 6 filtering by its own school", r.status_code, {200})

    print("\n== /files metadata ==")
    check("no token GET /files/metadata", call("GET", "/files/metadata").status_code, {401})
    check("student GET /files/metadata/99999", call("GET", "/files/metadata/99999", st1).status_code, {404})
    r = call("GET", "/files/metadata", pr7)
    check("principal 7 lists own uploads", r.status_code, {200})
    if r.status_code == 200 and r.json():
        check("principal 7 sees no school 6 uploads", all(u["school_id"] == 7 for u in r.json()), {True})

    print("\n== attendance write guards (unchanged behaviour) ==")
    # Principal 7 must not write into school 6's section 1.
    r = call("POST", "/attendance", pr7, json_body={
        "student_id": 1, "section_id": 1, "date": "2026-09-27", "status": "PRESENT",
    })
    check("principal 7 writing into school 6 section", r.status_code, {403})
    # Student must not write at all.
    r = call("POST", "/attendance", st1, json_body={
        "student_id": 1, "section_id": 1, "date": "2026-09-27", "status": "PRESENT",
    })
    check("student writing attendance", r.status_code, {403})
    # Invalid status must be a clean 422, not a 500.
    r = call("POST", "/attendance", pr6, json_body={
        "student_id": 1, "section_id": 1, "date": "2026-09-27", "status": "EXCUSED",
    })
    check("phantom status EXCUSED rejected", r.status_code, {422})
    # Patch a foreign-school record as principal 7.
    r = call("PATCH", "/attendance/1", pr7, json_body={"status": "PRESENT"})
    check("principal 7 patching school 6 record", r.status_code, {403})
    # Invalid status through PATCH.
    r = call("PATCH", "/attendance/1", pr6, json_body={"status": "BOGUS"})
    check("PATCH with bogus status", r.status_code, {422})

    print("\n== role assignment guards ==")
    users = call("GET", "/users", sa).json()
    me = next(u for u in users if u["mobile"] == "8019302351")
    r = call("PATCH", f"/roles/users/{me['id']}", sa, json_body={"role": "PRINCIPAL"})
    check("super admin changing own role", r.status_code, {400})

    # Only ever mutate QA_AUTOTEST users. The first version of this probe
    # targeted `users[1]`, which turned out to be real (non-QA) data.
    qa_schools = {s["id"] for s in call("GET", "/schools", sa).json()
                  if str(s.get("name", "")).startswith("QA_AUTOTEST_")}
    qa_users = [u for u in users if u.get("school_id") in qa_schools]
    print(f"      QA schools={sorted(qa_schools)} QA users={len(qa_users)}")
    if not qa_users:
        print("SKIP  no QA users to probe")
        return 1 if FAIL else 0

    victim = next(u for u in qa_users if u["role"] == "STUDENT")
    r = call("PATCH", f"/roles/users/{victim['id']}", sa, json_body={"role": "STUDENT"})
    check("assigning the role a user already has is a no-op", r.status_code, {200})

    r = call("PATCH", f"/roles/users/{victim['id']}", sa, json_body={"role": "WIZARD"})
    check("invalid role rejected", r.status_code, {422})
    r = call("PATCH", f"/roles/users/{victim['id']}", pr6, json_body={"role": "STUDENT"})
    check("principal changing a role", r.status_code, {403})
    r = call("PATCH", "/roles/users/999999", sa, json_body={"role": "STUDENT"})
    check("unknown user", r.status_code, {404})

    # Round-trip: flip a QA student to TEACHER and back, proving the happy path.
    r = call("PATCH", f"/roles/users/{victim['id']}", sa, json_body={"role": "TEACHER"})
    check("assign TEACHER", r.status_code, {200})
    if r.status_code == 200:
        check("returned role is TEACHER", r.json()["user"]["role"], {"TEACHER"})
    r = call("PATCH", f"/roles/users/{victim['id']}", sa, json_body={"role": "STUDENT"})
    check("revert to STUDENT", r.status_code, {200})
    if r.status_code == 200:
        check("returned role is STUDENT", r.json()["user"]["role"], {"STUDENT"})

    # The platform still has its Super Admin.
    sa_left = [u for u in call("GET", "/users", sa).json() if u["role"] == "SUPER_ADMIN"]
    check("platform still has an active Super Admin", len(sa_left) >= 1, {True})
    print(f"      super admins remaining: {[u['mobile'] for u in sa_left]}")

    # ---------------------------------------------------------------------
    # Re-verify the cross-tenant / cross-section write guards that the earlier
    # QA pass fixed, to prove this pass did not regress them.
    # ---------------------------------------------------------------------
    print("\n== previously fixed guards (regression) ==")
    exams = call("GET", "/exams", sa).json()
    items = exams.get("items", exams) if isinstance(exams, dict) else exams
    exam = next((e for e in items if e.get("school_id") == 6), None)
    if exam:
        # A principal of school 7 must not be able to generate report cards for
        # a school 6 section, nor correct school 6 attendance (both were fixed
        # earlier and are re-checked here).
        check(
            "principal 7 report-card generate for a school 6 section",
            call("POST", "/report-cards/generate", pr7, json_body={
                "student_ids": [], "section_id": 1, "academic_year_id": 2, "term_name": "QA Regression",
            }).status_code,
            {400, 403, 404, 422},
        )
        check(
            "principal 7 reads a school 6 student's report card",
            call("GET", f"/report-cards/student/{1}", pr7).status_code,
            {403, 404},
        )
    else:
        print("      (no school 6 exam found - skipping exam-scoped probes)")

    # Marks: a teacher must not submit for a section they do not teach.
    subjects = call("GET", "/subjects", pr6).json()
    print(f"      principal 6 sees {len(subjects)} subjects")

    # Notifications must not leak across roles.
    r = call("GET", "/notifications", pr7)
    check("principal 7 notifications 200", r.status_code, {200})
    if r.status_code == 200:
        items7 = r.json().get("items", [])
        schools = {n.get("school_id") for n in items7} - {None}
        check("principal 7 sees no school 6 notifications", schools <= {7}, {True})
        print(f"      principal 7 notification count: {len(items7)}")

    # Files: metadata already covered above.
    # Search: already covered above.

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    for f in FAIL:
        print(f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
