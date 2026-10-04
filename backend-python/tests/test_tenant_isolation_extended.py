"""Extended mandatory security tests A-H for the remaining routers.

Covers the domains not exercised by ``test_tenant_isolation.py``:

* teachers, principals, timetables, teacher-subjects, teacher-assignments
* grade-subjects, student-enrollments, notifications, search, files

...plus regression tests for four conditional fail-open findings that were
fixed in this pass (stray cross-tenant rows and orphaned enrollment rows).

Same A-H contract as the core suite:
  A cross-tenant read denied | B cross-tenant write denied
  C cross-tenant delete denied, row survives | D foreign-ref create rejected
  E lists scoped to caller's school | F missing tenant context fails closed
  G SUPER_ADMIN keeps cross-school access | H role gates hold
"""

from __future__ import annotations

import sqlite3

from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from tests.conftest import _TEST_DB_PATH
from tests.factories import (
    make_enrollment,
    make_grade_subject,
    make_notification,
    make_section,
    make_student,
    make_teacher,
    make_teacher_subject,
    make_timetable,
    make_upload,
    make_user,
)
from tests.helpers import auth

PREFIX = "/api/v1"


def _ids(resp_json, key="id"):
    if isinstance(resp_json, dict):
        rows = resp_json.get("items", resp_json.get("data", []))
    else:
        rows = resp_json
    return {row[key] for row in rows}


# ---------------------------------------------------------------------------
# A. Cross-tenant reads are denied
# ---------------------------------------------------------------------------


def test_a_extended_cross_tenant_reads_are_denied(client, db, world):
    h = auth(db, world.a.principal)  # caller belongs to school A
    a, b = world.a, world.b

    tt_b = make_timetable(db, b.school, b.year, b.grade, b.section, b.subject, b.teacher)
    tt_a = make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)
    upload_b = make_upload(db, b.school, b.principal)

    cases = [
        ("GET", f"/teachers/{b.teacher.id}", 403),
        ("GET", f"/principals/{b.principal.id}", 403),
        ("GET", f"/timetables/{tt_b.id}", 403),
        ("GET", f"/files/metadata/{upload_b.id}", 403),
        ("GET", f"/grade-subjects?grade_id={b.grade.id}", 403),
        (
            "GET",
            f"/teacher-assignments?teacher_id={b.teacher.id}&academic_year_id={b.year.id}",
            403,
        ),
        # A school_id query param from another school must be rejected.
        ("GET", f"/search?q=anything&school_id={b.school.id}", 403),
        # Super-admin-only surfaces.
        ("GET", "/principals", 403),
    ]
    for method, path, expected in cases:
        resp = client.request(method, f"{PREFIX}{path}", headers=h)
        assert resp.status_code == expected, (
            f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
        )

    # Controls: the very same endpoints work for the caller's own school.
    assert client.get(f"{PREFIX}/teachers/{a.teacher.id}", headers=h).status_code == 200
    assert client.get(f"{PREFIX}/timetables/{tt_a.id}", headers=h).status_code == 200
    own_upload = make_upload(db, a.school, a.principal)
    assert (
        client.get(f"{PREFIX}/files/metadata/{own_upload.id}", headers=h).status_code == 200
    )
    assert (
        client.get(f"{PREFIX}/grade-subjects?grade_id={a.grade.id}", headers=h).status_code
        == 200
    )


# ---------------------------------------------------------------------------
# B. Cross-tenant writes are denied
# ---------------------------------------------------------------------------


def test_b_extended_cross_tenant_writes_are_denied(client, db, world):
    h = auth(db, world.a.principal)
    a, b = world.a, world.b

    tt_b = make_timetable(db, b.school, b.year, b.grade, b.section, b.subject, b.teacher)
    ts_b = make_teacher_subject(db, b.teacher, b.subject, b.grade, b.section, b.school)
    gs_b = make_grade_subject(db, b.grade, b.subject)
    notif_b = make_notification(db, b.school, b.principal)

    enrollment_b = (
        db.query(StudentEnrollment)
        .filter_by(student_id=b.student.id)
        .one()
    )

    cases = [
        ("PATCH", f"/teachers/{b.teacher.id}", {"employee_id": "HACK"}, 403),
        ("PATCH", f"/principals/{b.principal.id}", {"display_name": "HACK"}, 403),
        ("PUT", f"/timetables/{tt_b.id}", {"day_of_week": "TUESDAY"}, 403),
        ("PATCH", f"/timetables/{tt_b.id}", {"day_of_week": "TUESDAY"}, 403),
        ("PATCH", f"/teacher-subjects/{ts_b.id}", {"grade_id": b.grade.id}, 403),
        ("DELETE", f"/teacher-subjects/{ts_b.id}", None, 403),
        ("POST", "/grade-subjects", {"grade_id": b.grade.id, "subject_id": b.subject.id}, 403),
        # Own grade but a foreign subject: rejected at validation (400).
        ("POST", "/grade-subjects", {"grade_id": a.grade.id, "subject_id": b.subject.id}, 400),
        (
            "PATCH",
            f"/student-enrollments/{enrollment_b.id}",
            {"section_id": a.section.id},
            403,
        ),
        ("DELETE", f"/teacher-assignments/{tt_b.id}", None, 403),
        # Class notification targeted at another school's class.
        (
            "POST",
            "/notifications/",
            {
                "notification_type": "CLASS_ONLY",
                "title": "Intruder",
                "message": "cross-tenant",
                "target_class_id": b.section.id,
            },
            403,
        ),
        # Foreign notification rows are not readable/mutable either.
        ("PATCH", f"/notifications/{notif_b.id}/read", None, 404),
        ("DELETE", f"/notifications/{notif_b.id}", None, 403),
        # Timetable create mixing references: first foreign ref wins (400).
        (
            "POST",
            "/timetables",
            {
                "grade_id": b.grade.id,
                "section_id": b.section.id,
                "subject_id": b.subject.id,
                "teacher_id": b.teacher.id,
                "academic_year_id": b.year.id,
                "start_time": "10:00",
                "end_time": "10:45",
                "day_of_week": "MONDAY",
            },
            400,
        ),
        # Enrollment create with a foreign student.
        (
            "POST",
            "/student-enrollments",
            {
                "student_id": b.student.id,
                "section_id": a.section.id,
                "academic_year_id": a.year.id,
            },
            403,
        ),
        # Enrollment create with a foreign section.
        (
            "POST",
            "/student-enrollments",
            {
                "student_id": a.student.id,
                "section_id": b.section.id,
                "academic_year_id": a.year.id,
            },
            403,
        ),
    ]

    for method, path, payload, expected in cases:
        resp = client.request(method, f"{PREFIX}{path}", headers=h, json=payload)
        assert resp.status_code == expected, (
            f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
        )

    # Nothing was mutated.
    db.expire_all()
    assert db.get(type(tt_b), tt_b.id) is not None
    assert db.get(type(ts_b), ts_b.id) is not None
    assert db.get(type(gs_b), gs_b.id) is not None
    assert db.get(type(notif_b), notif_b.id) is not None
    assert db.get(type(enrollment_b), enrollment_b.id) is not None
    assert notif_b.title != "Intruder"


# ---------------------------------------------------------------------------
# C. Cross-tenant deletes are denied and rows survive
# ---------------------------------------------------------------------------


def test_c_extended_cross_tenant_deletes_are_denied(client, db, world):
    h = auth(db, world.a.principal)
    a, b = world.a, world.b

    tt_b = make_timetable(db, b.school, b.year, b.grade, b.section, b.subject, b.teacher)
    ts_b = make_teacher_subject(db, b.teacher, b.subject, b.grade, b.section, b.school)
    gs_b = make_grade_subject(db, b.grade, b.subject)
    enrollment_b = (
        db.query(StudentEnrollment)
        .filter_by(student_id=b.student.id)
        .one()
    )

    cases = [
        ("DELETE", f"/timetables/{tt_b.id}", 403),
        ("DELETE", f"/teacher-subjects/{ts_b.id}", 403),
        ("DELETE", f"/grade-subjects/{gs_b.id}", 403),
        ("DELETE", f"/student-enrollments/{enrollment_b.id}", 403),
    ]
    for method, path, expected in cases:
        resp = client.request(method, f"{PREFIX}{path}", headers=h)
        assert resp.status_code == expected, (
            f"{method} {path} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
        )

    # Every school-B row still exists.
    db.expire_all()
    assert db.get(type(tt_b), tt_b.id) is not None
    assert db.get(type(ts_b), ts_b.id) is not None
    assert db.get(type(gs_b), gs_b.id) is not None
    assert db.get(type(enrollment_b), enrollment_b.id) is not None
    # Control: same-school upload delete works.
    up_a = make_upload(db, a.school, a.principal)
    assert client.delete(f"{PREFIX}/files/metadata/{up_a.id}", headers=h).status_code in (204, 405)


# ---------------------------------------------------------------------------
# E. List endpoints only return the caller's school
# ---------------------------------------------------------------------------


def test_e_extended_lists_are_scoped_to_own_school(client, db, world):
    h = auth(db, world.a.principal)
    a, b = world.a, world.b

    make_timetable(db, b.school, b.year, b.grade, b.section, b.subject, b.teacher)
    tt_a = make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)
    make_teacher_subject(db, b.teacher, b.subject, b.grade, b.section, b.school)
    make_teacher_subject(db, a.teacher, a.subject, a.grade, a.section, a.school)
    make_upload(db, b.school, b.principal)
    make_upload(db, a.school, a.principal)

    def items(path):
        resp = client.get(f"{PREFIX}{path}", headers=h)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        return data["items"] if isinstance(data, dict) else data

    teachers = items("/teachers")
    assert teachers and {t["school_id"] for t in teachers} == {a.school.id}
    assert b.teacher.id not in {t["id"] for t in teachers}

    timetables = items("/timetables")
    assert timetables and {t["school_id"] for t in timetables} == {a.school.id}
    assert tt_a.id in {t["id"] for t in timetables}

    ts_rows = items("/teacher-subjects")
    assert ts_rows  # school A row exists
    # A foreign teacher_id filter must yield nothing, not foreign rows.
    foreign_ts = items(f"/teacher-subjects?teacher_id={b.teacher.id}")
    assert foreign_ts == []

    enrollments = items(f"/student-enrollments?academic_year_id={a.year.id}")
    # Only school-A enrollments may appear; school B's row must be absent.
    assert enrollments
    assert not {e["id"] for e in enrollments} - enrollment_ids_for_school(db, a.school)
    b_enrollment_id = (
        db.query(StudentEnrollment.id)
        .join(Student, Student.id == StudentEnrollment.student_id)
        .filter(Student.school_id == b.school.id)
        .scalar()
    )
    assert b_enrollment_id not in {e["id"] for e in enrollments}

    uploads = items("/files/metadata")
    assert uploads and all(u["school_id"] == a.school.id for u in uploads)

    # Search only surfaces the caller's own subjects.
    resp = client.get(f"{PREFIX}/search?q=Subject", headers=h)
    assert resp.status_code == 200
    subject_ids = {s["id"] for s in resp.json()["subjects"]}
    assert a.subject.id in subject_ids
    assert b.subject.id not in subject_ids


def enrollment_ids_for_school(db, school) -> set:
    return {
        row.id
        for row in db.query(StudentEnrollment)
        .join(Student, Student.id == StudentEnrollment.student_id)
        .filter(Student.school_id == school.id)
        .all()
    }


# ---------------------------------------------------------------------------
# F. Missing tenant context fails closed (never open)
# ---------------------------------------------------------------------------


def test_f_extended_schoolless_non_super_admin_is_denied_everywhere(client, db, world):
    from tests.factories import make_user

    ghost = make_user(db, None, role="PRINCIPAL", display_name="Ghost Principal 2")
    h = auth(db, ghost)

    guarded_paths = [
        "/teachers",
        "/timetables",
        "/teacher-subjects",
        "/teacher-assignments?teacher_id=1&academic_year_id=1",
        "/grade-subjects?grade_id=1",
        f"/student-enrollments?academic_year_id={world.a.year.id}",
        "/notifications/",
        "/search?q=anything",
        "/files/metadata",
        "/principals/me",
        "/settings/principal",
        # Slip tests live under role prefixes (/teacher and /student), so both
        # are listed: the fail-closed guard must fire before any role check.
        "/teacher/slip-tests",
        "/teacher/slip-tests/classes",
        "/student/slip-tests",
    ]
    for path in guarded_paths:
        resp = client.get(f"{PREFIX}{path}", headers=h)
        assert resp.status_code == 403, (
            f"GET {path} -> {resp.status_code} (expected fail-closed 403): {resp.text[:300]}"
        )
        assert resp.json().get("detail") == "School context missing for this account", path

    # Mutations are denied by the same guard.
    assert client.post(f"{PREFIX}/timetables", headers=h, json={}).status_code == 403
    assert client.post(f"{PREFIX}/teacher-subjects", headers=h, json={}).status_code == 403
    assert client.post(f"{PREFIX}/grade-subjects", headers=h, json={}).status_code == 403
    assert (
        client.post(f"{PREFIX}/notifications/", headers=h, json={}).status_code == 403
    )


# ---------------------------------------------------------------------------
# G. SUPER_ADMIN keeps deliberate cross-school access
# ---------------------------------------------------------------------------


def test_g_extended_super_admin_cross_school_access(client, db, world):
    h = auth(db, world.superadmin)
    a, b = world.a, world.b

    make_timetable(db, b.school, b.year, b.grade, b.section, b.subject, b.teacher)
    make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)

    # Principals of both schools are visible (list is super-admin only).
    resp = client.get(f"{PREFIX}/principals", headers=h)
    assert resp.status_code == 200
    assert _ids(resp.json()) >= {a.principal.id, b.principal.id}

    # Teachers of both schools are visible.
    resp = client.get(f"{PREFIX}/teachers", headers=h)
    assert resp.status_code == 200
    assert _ids(resp.json()) >= {a.teacher.id, b.teacher.id}

    # Cross-school detail read works.
    assert client.get(f"{PREFIX}/teachers/{b.teacher.id}", headers=h).status_code == 200
    assert (
        client.get(f"{PREFIX}/principals/{b.principal.id}", headers=h).status_code == 200
    )


# ---------------------------------------------------------------------------
# H. Role gates
# ---------------------------------------------------------------------------


def test_h_extended_role_gates_hold(client, db, world):
    student = auth(db, world.a.student_user)
    teacher = auth(db, world.a.teacher_user)
    principal = auth(db, world.a.principal)
    a = world.a

    tt_a = make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)
    gs_a = make_grade_subject(db, a.grade, a.subject)

    # Students: no staff-management surfaces.
    assert client.post(f"{PREFIX}/timetables", headers=student, json={}).status_code == 403
    assert client.post(f"{PREFIX}/teacher-subjects", headers=student, json={}).status_code == 403
    assert client.delete(f"{PREFIX}/timetables/{tt_a.id}", headers=student).status_code == 403
    assert client.delete(f"{PREFIX}/grade-subjects/{gs_a.id}", headers=student).status_code == 403
    assert client.get(f"{PREFIX}/audit-logs", headers=student).status_code == 403
    assert client.get(f"{PREFIX}/roles", headers=student).status_code == 403
    assert client.get(f"{PREFIX}/reports/platform", headers=student).status_code == 403

    # Teachers: same (timetable writes are principal-only).
    assert client.post(f"{PREFIX}/timetables", headers=teacher, json={}).status_code == 403
    assert client.get(f"{PREFIX}/audit-logs", headers=teacher).status_code == 403

    # Principals: super-admin-only surfaces stay closed.
    assert client.get(f"{PREFIX}/audit-logs", headers=principal).status_code == 403
    assert client.get(f"{PREFIX}/roles", headers=principal).status_code == 403
    assert client.get(f"{PREFIX}/reports/platform", headers=principal).status_code == 403


# ---------------------------------------------------------------------------
# Regression tests for the four conditional fail-open findings
# ---------------------------------------------------------------------------


def test_fix_notification_class_teacher_lookup_is_school_scoped(client, db, world):
    """A school-B section listing a school-A teacher as class teacher must not
    expose school B's roster (class-info) or accept class notifications."""
    a, b = world.a, world.b

    lonely_user = make_user(db, a.school, role="TEACHER", display_name="Lonely A")
    lonely = make_teacher(db, a.school, user=lonely_user)
    # Anomalous row: school-B section claims a school-A teacher.
    make_section(db, b.grade, name="B-XX", class_teacher_id=lonely.id)

    h = auth(db, lonely_user)
    resp = client.get(f"{PREFIX}/notifications/teacher/class-info", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_class_teacher"] is False
    assert body["students"] == []

    # Posting a class notification is refused for the same reason.
    resp = client.post(
        f"{PREFIX}/notifications/",
        headers=h,
        json={
            "notification_type": "ONLY_FOR_CLASS",
            "title": "Intruder class",
            "message": "cross-tenant",
        },
    )
    assert resp.status_code == 403
    assert "Class Teacher" in resp.json()["detail"]

    # Control: a real class teacher still sees their own class.
    ok = client.get(f"{PREFIX}/notifications/teacher/class-info", headers=auth(db, a.teacher_user))
    assert ok.status_code == 200
    assert ok.json()["is_class_teacher"] is True
    assert ok.json()["section_id"] == a.section.id


def test_fix_search_teacher_subjects_are_school_scoped(client, db, world):
    """Stray cross-tenant teacher_subjects rows must never surface another
    school's subjects in search results (two layers: assignment row + school
    filter on the subject query)."""
    a, b = world.a, world.b

    teacher_user = make_user(db, a.school, role="TEACHER", display_name="Searcher A")
    teacher = make_teacher(db, a.school, user=teacher_user)

    # Layer 1 test: assignment row claims school B outright.
    make_teacher_subject(db, teacher, b.subject, b.grade, b.section, b.school)
    # Layer 2 test: assignment row claims school A but points at B's subject.
    make_teacher_subject(db, teacher, b.subject, a.grade, a.section, a.school)
    # Control: a legitimate school-A assignment.
    make_teacher_subject(db, teacher, a.subject, a.grade, a.section, a.school)

    h = auth(db, teacher_user)

    resp = client.get(f"{PREFIX}/search?q={b.subject.name}", headers=h)
    assert resp.status_code == 200
    assert b.subject.id not in {s["id"] for s in resp.json()["subjects"]}

    resp = client.get(f"{PREFIX}/search?q={a.subject.name}", headers=h)
    assert resp.status_code == 200
    assert a.subject.id in {s["id"] for s in resp.json()["subjects"]}, (
        "the school scoping must not hide the caller's own subjects"
    )


def test_fix_teacher_assignments_list_is_school_scoped(client, db, world):
    """GET /teacher-assignments filters timetables by school for non-super
    admins, so an anomalous cross-tenant timetable row is invisible."""
    a, b = world.a, world.b

    legit = make_timetable(
        db, a.school, a.year, a.grade, a.section, a.subject, a.teacher
    )
    # Anomalous row: school-B timetable attached to school A's teacher.
    anomalous = make_timetable(
        db, b.school, a.year, b.grade, b.section, b.subject, a.teacher
    )

    h = auth(db, a.principal)
    resp = client.get(
        f"{PREFIX}/teacher-assignments?teacher_id={a.teacher.id}"
        f"&academic_year_id={a.year.id}",
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    seen = _ids(resp.json())
    assert legit.id in seen
    assert anomalous.id not in seen

    # Control: SUPER_ADMIN still sees both (deliberate cross-school view).
    admin = auth(db, world.superadmin)
    resp = client.get(
        f"{PREFIX}/teacher-assignments?teacher_id={a.teacher.id}"
        f"&academic_year_id={a.year.id}",
        headers=admin,
    )
    assert resp.status_code == 200
    assert _ids(resp.json()) >= {legit.id, anomalous.id}


def test_fix_orphan_enrollment_delete_fails_closed(client, db, world):
    """An enrollment whose student row is missing has no tenant attribution,
    so only SUPER_ADMIN may delete it (mirrors the PATCH check)."""
    from app.models.student_enrollment import StudentEnrollment

    orphan_student = make_student(db, world.b.school)
    enrollment = make_enrollment(
        db, orphan_student, world.b.year, world.b.section, roll_number="ZZ9"
    )
    enrollment_id = enrollment.id
    student_id = orphan_student.id

    # Routers and the test share one connection; commit so the row is
    # visible to the short-lived out-of-band connection below.
    db.commit()

    # Remove the student row from a separate connection where SQLite runs
    # with foreign keys OFF (the pragma default), producing a legacy-style
    # orphan row exactly like an interrupted import would.
    conn = sqlite3.connect(_TEST_DB_PATH, timeout=10)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
    finally:
        conn.close()

    db.expire_all()
    h = auth(db, world.a.principal)
    resp = client.delete(f"{PREFIX}/student-enrollments/{enrollment_id}", headers=h)
    assert resp.status_code == 403, resp.text

    # The row survives.
    assert db.get(StudentEnrollment, enrollment_id) is not None

    # SUPER_ADMIN (the only role without a school) can still clean it up.
    admin = auth(db, world.superadmin)
    resp = client.delete(f"{PREFIX}/student-enrollments/{enrollment_id}", headers=admin)
    assert resp.status_code == 204, resp.text
    assert db.get(StudentEnrollment, enrollment_id) is None
