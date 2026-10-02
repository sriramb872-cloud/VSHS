"""Mandatory security tests A-H: multi-school tenant isolation.

Every test proves server-side enforcement - the UI never decides who sees what.

* **A** cross-tenant *read* of an object is denied (exact per-domain codes)
* **B** cross-tenant *write* (PATCH/PUT/POST mutations) is denied
* **C** cross-tenant *delete* is denied and the row survives
* **D** *create* with foreign-school references is rejected and nothing persists
* **E** list endpoints only ever return the caller's school
* **F** a non-super-admin account without tenant context fails CLOSED (403)
* **G** SUPER_ADMIN keeps deliberate cross-school access
* **H** role gates hold for every role (student/teacher/admin)
"""

from __future__ import annotations

from app.models.announcement import Announcement
from app.models.attendance import Attendance
from app.models.exam import Exam
from app.models.homework import Homework
from app.models.report_card import ReportCard
from app.models.section import Section
from app.models.student import Student
from tests.factories import make_student, make_user
from tests.helpers import auth

PREFIX = "/api/v1"


def _count(db, model) -> int:
    return db.query(model).count()


def _snapshot(db) -> dict:
    return {
        "sections": _count(db, Section),
        "students": _count(db, Student),
        "homework": _count(db, Homework),
        "announcements": _count(db, Announcement),
        "exams": _count(db, Exam),
        "attendance": _count(db, Attendance),
        "report_cards": _count(db, ReportCard),
    }


# ---------------------------------------------------------------------------
# A. Cross-tenant reads are denied
# ---------------------------------------------------------------------------


def test_a_cross_tenant_detail_reads_are_denied(client, db, world):
    h = auth(db, world.a.principal)  # caller belongs to school A
    b = world.b

    cases = [
        # (method, path, expected status) - 403 = "exists but not yours",
        # 404 = "no existence oracle" (deliberate per-domain convention).
        ("GET", f"/grades/{b.grade.id}", 403),
        ("GET", f"/sections/{b.section.id}", 403),
        ("GET", f"/subjects/{b.subject.id}", 403),
        ("GET", f"/students/{b.student.id}", 403),
        ("GET", f"/users/{b.principal.id}", 403),
        ("GET", f"/academic-years/{b.year.id}", 403),
        ("GET", f"/exams/{b.exam.id}", 404),
        ("GET", f"/exams/{b.exam.id}/subjects", 404),
        ("GET", f"/exams/{b.exam.id}/marks-status", 404),
        ("GET", f"/homework/{b.homework.id}", 404),
        ("GET", f"/announcements/{b.announcement.id}", 404),
        ("GET", f"/calendar-events/{b.event.id}", 403),
        (
            "GET",
            f"/report-cards/{b.student.id}?academic_year_id={b.year.id}",
            403,
        ),
        ("GET", f"/attendance/student/{b.student.id}", 403),
        # Reads filtered by a foreign query parameter must be denied too.
        ("GET", f"/attendance?section_id={b.section.id}", 403),
    ]

    for method, path, expected in cases:
        resp = client.request(method, f"{PREFIX}{path}", headers=h)
        assert resp.status_code == expected, (
            f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
        )


def test_a_control_own_school_reads_work(client, db, world):
    """The denials above must be tenant-based, not blanket denial."""
    h = auth(db, world.a.principal)
    a = world.a

    assert client.get(f"{PREFIX}/grades/{a.grade.id}", headers=h).status_code == 200
    assert client.get(f"{PREFIX}/sections/{a.section.id}", headers=h).status_code == 200
    assert client.get(f"{PREFIX}/subjects/{a.subject.id}", headers=h).status_code == 200
    assert client.get(f"{PREFIX}/students/{a.student.id}", headers=h).status_code == 200
    assert client.get(f"{PREFIX}/exams/{a.exam.id}", headers=h).status_code == 200
    assert client.get(f"{PREFIX}/homework/{a.homework.id}", headers=h).status_code == 200
    assert (
        client.get(f"{PREFIX}/calendar-events/{a.event.id}", headers=h).status_code == 200
    )


# ---------------------------------------------------------------------------
# B. Cross-tenant writes are denied
# ---------------------------------------------------------------------------


def test_b_cross_tenant_writes_are_denied(client, db, world):
    h = auth(db, world.a.principal)
    b = world.b

    cases = [
        ("PATCH", f"/grades/{b.grade.id}", {"name": "Intruder Grade"}, 403),
        ("PATCH", f"/sections/{b.section.id}", {"name": "ZZ"}, 403),
        ("PATCH", f"/subjects/{b.subject.id}", {"name": "Intruder Subject"}, 403),
        ("PATCH", f"/students/{b.student.id}", {"display_name": "Intruder"}, 403),
        ("PATCH", f"/users/{b.principal.id}", {"display_name": "Intruder"}, 403),
        ("PATCH", f"/academic-years/{b.year.id}", {"name": "2099-2100"}, 403),
        ("PATCH", f"/exams/{b.exam.id}", {"name": "Intruder Exam"}, 404),
        ("PATCH", f"/homework/{b.homework.id}", {"title": "Intruder HW"}, 404),
        ("PUT", f"/announcements/{b.announcement.id}", {"title": "Intruder"}, 404),
        ("PUT", f"/calendar-events/{b.event.id}", {"title": "Intruder"}, 403),
        ("PATCH", f"/calendar-events/{b.event.id}", {"title": "Intruder"}, 403),
        ("PATCH", f"/attendance/{b.attendance.id}", {"status": "ABSENT"}, 403),
        ("POST", f"/attendance/{b.attendance.id}/void", None, 403),
        ("POST", f"/exams/{b.exam.id}/archive", None, 404),
        ("POST", f"/exams/{b.exam.id}/reopen-marks", None, 404),
        ("POST", f"/exams/{b.exam.id}/republish", None, 404),
        ("POST", f"/exams/{b.exam.id}/publish", None, 404),
        (
            "POST",
            f"/users/{b.teacher_user.id}/reset-password",
            {"password": "Password1234"},
            403,
        ),
        ("POST", f"/users/{b.teacher_user.id}/revoke-sessions", None, 403),
        (
            "POST",
            "/marks/submit",
            {
                "exam_subject_id": b.exam_subject.id,
                "marks": [{"student_id": b.student.id, "marks_obtained": 55.0}],
            },
            403,
        ),
        (
            "PATCH",
            f"/report-cards/{b.student.id}/remarks?academic_year_id={b.year.id}",
            {"teacher_remarks": "Intruder remark"},
            403,
        ),
        (
            "POST",
            "/report-cards/generate"
            f"?section_id={b.section.id}&academic_year_id={b.year.id}"
            f"&exam_id={b.exam.id}&term_name=Term%201",
            None,
            403,
        ),
    ]

    for method, path, payload, expected in cases:
        resp = client.request(
            method, f"{PREFIX}{path}", headers=h, json=payload
        )
        assert resp.status_code == expected, (
            f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
        )

    # Nothing was mutated: spot-check school B's rows.
    db.refresh(world.b.grade)
    db.refresh(world.b.section)
    db.refresh(world.b.subject)
    db.refresh(world.b.event)
    assert world.b.grade.name != "Intruder Grade"
    assert world.b.section.name != "ZZ"
    assert world.b.subject.name != "Intruder Subject"
    assert world.b.event.title != "Intruder"


def test_b_cross_tenant_marks_submission_is_denied_for_teacher(client, db, world):
    """A school-A teacher must not write into a school-B exam, even though
    the teacher has marks-submission rights in their own school."""
    h = auth(db, world.a.teacher_user)
    b = world.b

    resp = client.post(
        f"{PREFIX}/marks/submit",
        headers=h,
        json={
            "exam_subject_id": b.exam_subject.id,
            "marks": [{"student_id": b.student.id, "marks_obtained": 70.0}],
        },
    )
    assert resp.status_code == 403

    resp_formative = client.post(
        f"{PREFIX}/marks/submit-formative",
        headers=h,
        json={
            "exam_subject_id": b.exam_subject.id,
            "marks": [{"student_id": b.student.id, "written_test": 10}],
        },
    )
    assert resp_formative.status_code == 403


# ---------------------------------------------------------------------------
# C. Cross-tenant deletes are denied and rows survive
# ---------------------------------------------------------------------------


def test_c_cross_tenant_deletes_are_denied(client, db, world):
    h = auth(db, world.a.principal)
    b = world.b

    cases = [
        ("DELETE", f"/grades/{b.grade.id}", 403),
        ("DELETE", f"/sections/{b.section.id}", 403),
        ("DELETE", f"/subjects/{b.subject.id}", 403),
        ("DELETE", f"/academic-years/{b.year.id}", 403),
        ("DELETE", f"/exams/{b.exam.id}", 404),
        ("DELETE", f"/homework/{b.homework.id}", 404),
        ("DELETE", f"/announcements/{b.announcement.id}", 404),
        ("DELETE", f"/calendar-events/{b.event.id}", 403),
    ]
    for method, path, expected in cases:
        resp = client.request(method, f"{PREFIX}{path}", headers=h)
        assert resp.status_code == expected, (
            f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
        )

    # Every school-B row still exists.
    db.expire_all()
    assert db.get(type(world.b.grade), world.b.grade.id) is not None
    assert db.get(type(world.b.section), world.b.section.id) is not None
    assert db.get(type(world.b.subject), world.b.subject.id) is not None
    assert db.get(type(world.b.year), world.b.year.id) is not None
    assert db.get(Exam, world.b.exam.id) is not None
    assert db.get(Homework, world.b.homework.id) is not None
    assert db.get(Announcement, world.b.announcement.id) is not None
    assert db.get(type(world.b.event), world.b.event.id) is not None


# ---------------------------------------------------------------------------
# D. Creates with foreign-school references are rejected (nothing persists)
# ---------------------------------------------------------------------------


def test_d_create_with_foreign_references_is_rejected(client, db, world):
    h = auth(db, world.a.principal)
    a, b = world.a, world.b

    before = _snapshot(db)

    cases = [
        # section whose grade belongs to school B
        (
            "POST",
            "/sections",
            {"name": "Intruder Section", "grade_id": b.grade.id},
            400,
        ),
        # student placed into school B's section
        ("POST", "/students", {"section_id": b.section.id}, 403),
        # announcement scoped to school B's grade
        (
            "POST",
            "/announcements/",
            {
                "title": "Intruder announcement",
                "description": "cross-tenant",
                "audience": "Grade",
                "grade_id": b.grade.id,
                "publish_date": "2025-06-01T00:00:00",
                "status": "Published",
            },
            400,
        ),
        # exam mixing school A's grade with school B's section
        (
            "POST",
            "/exams/",
            {
                "name": "Intruder Exam",
                "exam_type": "Summative Assessment",
                "assessment_mode": "SUMMATIVE",
                "academic_year_id": a.year.id,
                "grade_id": a.grade.id,
                "section_id": b.section.id,
                "start_date": "2025-09-01",
                "end_date": "2025-09-10",
            },
            400,
        ),
        # attendance recorded against school B's section
        (
            "POST",
            "/attendance/",
            {
                "student_id": b.student.id,
                "section_id": b.section.id,
                "date": "2025-06-03",
                "status": "PRESENT",
            },
            (400, 403),
        ),
        # report-card generation for school B's section
        (
            "POST",
            f"/report-cards/generate?section_id={b.section.id}"
            f"&academic_year_id={b.year.id}&exam_id={b.exam.id}&term_name=Term%201",
            None,
            403,
        ),
        # marks submitted for school B's exam subject
        (
            "POST",
            "/marks/submit",
            {
                "exam_subject_id": b.exam_subject.id,
                "marks": [{"student_id": b.student.id, "marks_obtained": 40.0}],
            },
            403,
        ),
    ]

    for method, path, payload, expected in cases:
        resp = client.request(method, f"{PREFIX}{path}", headers=h, json=payload)
        if isinstance(expected, tuple):
            assert resp.status_code in expected, (
                f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
            )
        else:
            assert resp.status_code == expected, (
                f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
            )

    # Not a single row was created by any of the rejected requests.
    assert _snapshot(db) == before


def test_d_foreign_references_rejected_for_super_created_entities(client, db, world):
    """Even SUPER_ADMIN creates must validate referenced IDs (400, no 500)."""
    h = auth(db, world.superadmin)
    resp = client.post(
        f"{PREFIX}/sections",
        headers=h,
        json={"name": "Orphan Section", "school_id": world.a.school.id, "grade_id": 99_999},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# E. List endpoints only return the caller's school
# ---------------------------------------------------------------------------


def test_e_principal_lists_are_scoped_to_own_school(client, db, world):
    h = auth(db, world.a.principal)
    a, b = world.a, world.b

    def items(path):
        body = client.get(f"{PREFIX}{path}", headers=h)
        assert body.status_code == 200, f"{path} -> {body.status_code}: {body.text[:300]}"
        data = body.json()
        return data["items"] if isinstance(data, dict) else data

    grades = items("/grades")
    assert grades and {g["school_id"] for g in grades} == {a.school.id}

    sections = items("/sections")
    assert sections and {s["school_id"] for s in sections} == {a.school.id}

    subjects = items("/subjects")
    assert subjects and {s["school_id"] for s in subjects} == {a.school.id}

    students = items("/students")
    assert students and {s["school_id"] for s in students} == {a.school.id}

    users = items("/users")
    assert users and {u["school_id"] for u in users} == {a.school.id}

    years = items("/academic-years")
    assert years and {y["school_id"] for y in years} == {a.school.id}

    exams = items("/exams/")
    assert exams and {e["school_id"] for e in exams} == {a.school.id}
    assert b.exam.id not in {e["id"] for e in exams}

    events = items("/calendar-events/")
    assert events and {e["school_id"] for e in events} == {a.school.id}

    homework = items("/homework/")
    assert homework and {hw["id"] for hw in homework} == {a.homework.id}

    announcements = items("/announcements/")
    assert announcements and {an["id"] for an in announcements} == {a.announcement.id}

    marks = items("/marks/")
    assert marks and all(m["student_id"] == a.student.id for m in marks)

    report_cards = items("/report-cards/")
    assert report_cards and all(
        rc["student_id"] == a.student.id for rc in report_cards
    )

    # Foreign filter parameters must not widen the scope (empty, not leaked).
    foreign_students = items(f"/students?section_id={b.section.id}")
    assert foreign_students == []
    foreign_marks = items(f"/marks/?exam_id={b.exam.id}")
    assert foreign_marks == []


def test_e_teacher_list_is_pinned_to_own_school_and_class(client, db, world):
    h = auth(db, world.a.teacher_user)
    a, b = world.a, world.b

    students = client.get(f"{PREFIX}/students", headers=h)
    assert students.status_code == 200
    rows = students.json()
    assert rows and all(s["school_id"] == a.school.id for s in rows)
    assert b.student.id not in {s["id"] for s in rows}

    exams = client.get(f"{PREFIX}/exams/", headers=h)
    assert exams.status_code == 200
    assert b.exam.id not in {e["id"] for e in exams.json()["items"]}


# ---------------------------------------------------------------------------
# F. Missing tenant context fails closed (never open)
# ---------------------------------------------------------------------------


def test_f_schoolless_non_super_admin_is_denied_everywhere(client, db, world):
    """A non-super-admin without a school is a misconfigured account. Every
    tenant-scoped endpoint must deny it (fail closed) instead of running its
    query unfiltered and returning OTHER schools' data."""
    ghost = make_user(db, None, role="PRINCIPAL", display_name="Ghost Principal")
    h = auth(db, ghost)

    guarded_paths = [
        "/grades",
        "/sections",
        "/subjects",
        "/students",
        "/users",
        "/academic-years",
        "/exams/",
        "/homework/",
        "/announcements/",
        "/calendar-events/",
        "/marks/",
        "/report-cards/",
        "/attendance",
        "/dashboard/principal",
        "/dashboard/teacher",
        "/auth/me",
    ]
    for path in guarded_paths:
        resp = client.get(f"{PREFIX}{path}", headers=h)
        assert resp.status_code == 403, (
            f"GET {path} -> {resp.status_code} (expected fail-closed 403): {resp.text[:300]}"
        )
        assert resp.json().get("detail") == "School context missing for this account"

    # Mutations are denied by the same guard.
    assert client.post(f"{PREFIX}/grades", headers=h, json={"name": "G"}).status_code == 403
    assert client.post(f"{PREFIX}/exams/", headers=h, json={}).status_code == 403


def test_f_ghost_account_can_be_repaired_by_super_admin(client, db, world):
    """Fail-closed must be recoverable: SUPER_ADMIN can re-attach the school."""
    ghost = make_user(db, None, role="PRINCIPAL", display_name="Ghost Principal")
    ghost_headers = auth(db, ghost)
    admin_headers = auth(db, world.superadmin)

    assert client.get(f"{PREFIX}/grades", headers=ghost_headers).status_code == 403

    repair = client.patch(
        f"{PREFIX}/users/{ghost.id}",
        headers=admin_headers,
        json={"school_id": world.a.school.id},
    )
    assert repair.status_code == 200, repair.text
    assert repair.json()["school_id"] == world.a.school.id

    # Now the same account is usable - but only for school A.
    ok = client.get(f"{PREFIX}/grades", headers=ghost_headers)
    assert ok.status_code == 200
    assert {g["school_id"] for g in ok.json()} == {world.a.school.id}

    # ...and school B stays off-limits.
    assert (
        client.get(f"{PREFIX}/students/{world.b.student.id}", headers=ghost_headers).status_code
        == 403
    )


def test_f_super_admin_without_school_context_is_exempt(client, db, world):
    """SUPER_ADMIN is the only role allowed to be school-less; endpoints that
    genuinely need a school still say so with a 400, not a leak."""
    h = auth(db, world.superadmin)
    resp = client.get(f"{PREFIX}/grades", headers=h)
    assert resp.status_code == 400
    assert "School context" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# G. SUPER_ADMIN keeps deliberate cross-school access
# ---------------------------------------------------------------------------


def test_g_super_admin_cross_school_access(client, db, world):
    h = auth(db, world.superadmin)
    a, b = world.a, world.b

    # Read school B's directory filtered by school.
    users = client.get(f"{PREFIX}/users?school_id={b.school.id}", headers=h)
    assert users.status_code == 200
    assert users.json() and all(u["school_id"] == b.school.id for u in users.json())

    students = client.get(f"{PREFIX}/students?school_id={b.school.id}", headers=h)
    assert students.status_code == 200
    assert any(s["id"] == b.student.id for s in students.json())

    # Unfiltered lists span both schools (deliberate cross-school view).
    exams = client.get(f"{PREFIX}/exams/", headers=h)
    assert exams.status_code == 200
    exam_ids = {e["id"] for e in exams.json()["items"]}
    assert {a.exam.id, b.exam.id} <= exam_ids

    # Cross-school write is allowed for SUPER_ADMIN.
    patch = client.patch(
        f"{PREFIX}/grades/{b.grade.id}", headers=h, json={"name": "Renamed By Platform"}
    )
    assert patch.status_code == 200
    db.refresh(b.grade)
    assert b.grade.name == "Renamed By Platform"

    # Cross-school read of an object school A cannot see.
    detail = client.get(f"{PREFIX}/students/{b.student.id}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["school_id"] == b.school.id


# ---------------------------------------------------------------------------
# H. Role gates
# ---------------------------------------------------------------------------


def test_h_student_cannot_reach_admin_surfaces(client, db, world):
    h = auth(db, world.a.student_user)

    assert client.get(f"{PREFIX}/users", headers=h).status_code == 403
    assert client.get(f"{PREFIX}/dashboard/principal", headers=h).status_code == 403
    assert client.get(f"{PREFIX}/dashboard/teacher", headers=h).status_code == 403
    assert client.post(f"{PREFIX}/grades", headers=h, json={"name": "X"}).status_code == 403
    assert client.post(
        f"{PREFIX}/exams/",
        headers=h,
        json={
            "name": "X",
            "exam_type": "FA",
            "academic_year_id": world.a.year.id,
            "grade_id": world.a.grade.id,
            "section_id": world.a.section.id,
            "start_date": "2025-09-01",
            "end_date": "2025-09-02",
        },
    ).status_code == 403
    assert client.post(
        f"{PREFIX}/marks/submit",
        headers=h,
        json={
            "exam_subject_id": world.a.exam_subject.id,
            "marks": [{"student_id": world.a.student.id, "marks_obtained": 10}],
        },
    ).status_code == 403
    # Cross-school read of another student is denied for a student too.
    assert client.get(f"{PREFIX}/students/{world.b.student.id}", headers=h).status_code == 403


def test_h_student_can_read_only_own_profile(client, db, world):
    own = auth(db, world.a.student_user)
    # Another student of the SAME school (so tenant checks don't mask the
    # role rule).
    other = make_student(db, world.a.school)

    assert client.get(f"{PREFIX}/students/me", headers=own).status_code == 200
    assert client.get(f"{PREFIX}/students/{world.a.student.id}", headers=own).status_code == 200
    assert client.get(f"{PREFIX}/students/{other.id}", headers=own).status_code == 403


def test_h_teacher_cannot_reach_admin_surfaces(client, db, world):
    h = auth(db, world.a.teacher_user)

    assert client.get(f"{PREFIX}/users", headers=h).status_code == 403
    assert client.delete(f"{PREFIX}/grades/{world.a.grade.id}", headers=h).status_code == 403
    assert client.post(f"{PREFIX}/calendar-events/", headers=h, json={}).status_code == 403
    assert (
        client.post(
            f"{PREFIX}/users/{world.a.student.user_id}/reset-password",
            headers=h,
            json={"password": "Password1234"},
        ).status_code
        == 403
    )


def test_h_principal_cannot_reach_super_admin_only_surfaces(client, db, world):
    h = auth(db, world.a.principal)

    assert client.get(f"{PREFIX}/dashboard/super-admin", headers=h).status_code == 403
    assert client.get(f"{PREFIX}/schools", headers=h).status_code in (403, 200)
    # Creating a school is super-admin only.
    resp = client.post(
        f"{PREFIX}/schools", headers=h, json={"name": "Rogue School", "code": "ROGUE1"}
    )
    assert resp.status_code == 403


def test_h_unauthenticated_and_foreign_tokens_are_rejected(client, db, world):
    # No token at all.
    assert client.get(f"{PREFIX}/grades").status_code == 401
    # Garbage token.
    assert client.get(
        f"{PREFIX}/grades", headers={"Authorization": "Bearer garbage.token.here"}
    ).status_code == 401
    # Correct scheme, wrong value.
    assert client.get(
        f"{PREFIX}/grades", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    ).status_code == 401
