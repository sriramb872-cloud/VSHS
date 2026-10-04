"""Slip tests — authorization, validation, notification fan-out, soft cancel.

Every test proves SERVER-side enforcement. The teacher portal's class picker and
the student portal's tabs are cosmetic: the API is the only authority.

Covered groups
--------------
1. **Authorization** — unassigned teacher, other teacher's test, cross-school,
   student cross-class, wrong role (student→teacher API, principal/super admin
   → both APIs).
2. **Validation** — title, max_marks bounds, description length, past date,
   date outside the academic year, closed year, HTML sanitisation.
3. **Notifications** — per-student fan-out, no leakage outside the class,
   inactive students skipped, empty class notified to nobody, rollback, deep-link
   fields, and "only a student-visible change earns a notice".
4. **Soft cancel** — no hard delete, cancelled row still student-visible,
   editing a cancelled test is a 409, cancel is idempotent.
5. **Derived filters** — upcoming/past/all split from the school-local date.
"""
from __future__ import annotations

from datetime import date, time, timedelta

import pytest

from app.models.notification import Notification
from app.models.slip_test import SlipTest
from tests.factories import (
    make_enrollment,
    make_grade,
    make_section,
    make_slip_test,
    make_student,
    make_subject,
    make_teacher,
    make_teacher_subject,
    make_timetable,
    make_user,
)
from tests.helpers import auth

PREFIX = "/api/v1"
TEACHER = f"{PREFIX}/teacher/slip-tests"
STUDENT = f"{PREFIX}/student/slip-tests"

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
IN_TWO_DAYS = (date.today() + timedelta(days=2)).isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def years(db, world):
    """Widen both schools' ACTIVE year so it actually contains today.

    `tests.world.build_school` uses a fixed 2025-04-01 .. 2026-03-31 window,
    which stops containing today. Slip tests legitimately refuse a date outside
    the academic year, so the window is widened here. Pure test scaffolding —
    no production behaviour is relaxed.
    """
    today = date.today()
    for school in (world.a, world.b):
        school.year.start_date = today - timedelta(days=60)
        school.year.end_date = today + timedelta(days=300)
    db.flush()
    return world


@pytest.fixture
def school_a(years):
    """School A, with no teaching assignments yet."""
    return years.a


@pytest.fixture
def assigned(db, years):
    """Teacher A of school A, assigned to A's grade/section/subject.

    Uses a timetable row, the same source the Principal Timetable page writes
    and the teacher portal's own class picker reads back.
    """
    a = years.a
    make_timetable(
        db,
        a.school,
        a.year,
        a.grade,
        a.section,
        a.subject,
        a.teacher,
    )
    return a


def create_payload(world, **overrides):
    body = {
        "grade_id": world.grade.id,
        "section_id": world.section.id,
        "subject_id": world.subject.id,
        "academic_year_id": world.year.id,
        "title": "Unit 3 Quiz",
        "description": "Chapters 5 and 6",
        "scheduled_date": TOMORROW,
        "max_marks": 20,
    }
    body.update(overrides)
    return body


def notifications_for(db, user):
    """Newest first, matching how ``GET /notifications/`` orders them."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .all()
    )


def slip_notifications(db, user):
    return [n for n in notifications_for(db, user) if n.category == "SLIP_TEST"]


# ---------------------------------------------------------------------------
# 1. Authorization
# ---------------------------------------------------------------------------


def test_teacher_cannot_create_for_unassigned_class(client, db, school_a):
    """A teacher with no assignment at all gets 403, never a written row."""
    h = auth(db, school_a.teacher_user)

    assert client.post(
        f"{TEACHER}", json=create_payload(school_a), headers=h
    ).status_code == 403
    assert db.query(SlipTest).count() == 0


def test_teacher_cannot_create_for_other_schools_class(client, db, world):
    """Class ids from another school are refused, not silently reassigned."""
    a, b = world.a, world.b
    a.year.start_date = date.today() - timedelta(days=60)
    a.year.end_date = date.today() + timedelta(days=300)
    db.flush()

    make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)
    h = auth(db, a.teacher_user)

    res = client.post(
        f"{TEACHER}",
        json=create_payload(a, grade_id=b.grade.id,
                            section_id=b.section.id,
                            subject_id=b.subject.id),
        headers=h,
    )
    assert res.status_code == 403
    assert db.query(SlipTest).count() == 0


def test_teacher_cannot_list_unassigned_class(client, db, assigned, years):
    """The list endpoint cannot be used to probe classes she does not teach."""
    h = auth(db, assigned.teacher_user)

    # She IS assigned to this exact combination - 200, and an empty list.
    allowed = client.get(
        f"{TEACHER}",
        params={"class": assigned.section.id, "subject": assigned.subject.id},
        headers=h,
    )
    assert allowed.status_code == 200
    assert allowed.json()["total"] == 0

    # A subject she does not teach in that class.
    other_subject = make_subject(db, assigned.school, name="Physics")
    assert client.get(
        f"{TEACHER}",
        params={"class": assigned.section.id, "subject": other_subject.id},
        headers=h,
    ).status_code == 403

    # A section she is not assigned to at all.
    other_section = make_section(db, assigned.grade, name="B")
    assert client.get(
        f"{TEACHER}",
        params={"class": other_section.id, "subject": assigned.subject.id},
        headers=h,
    ).status_code == 403

    # Another school's class answers 400, not 403: the school filter makes it
    # indistinguishable from a class id that does not exist, so the endpoint is
    # not a cross-tenant existence oracle.
    other_school_section = make_section(db, years.b.grade, name="X")
    assert client.get(
        f"{TEACHER}",
        params={"class": other_school_section.id, "subject": assigned.subject.id},
        headers=h,
    ).status_code == 400

    # Same for a class id that does not exist at all.
    assert client.get(
        f"{TEACHER}",
        params={"class": 999999, "subject": assigned.subject.id},
        headers=h,
    ).status_code == 400


def test_teacher_cannot_touch_another_teachers_slip_test(client, db, assigned):
    row = make_slip_test(
        db, assigned.school, assigned.teacher, assigned.grade, assigned.section,
        assigned.subject, assigned.year,
    )

    other_user = make_user(db, assigned.school, role="TEACHER")
    make_teacher(db, assigned.school, user=other_user)
    h = auth(db, other_user)

    assert client.get(f"{TEACHER}/{row.id}", headers=h).status_code == 404
    assert client.put(
        f"{TEACHER}/{row.id}", json={"title": "Hijacked"}, headers=h
    ).status_code == 404
    assert client.post(f"{TEACHER}/{row.id}/cancel", headers=h).status_code == 404

    db.refresh(row)
    assert row.status == "scheduled"
    assert row.title == "Unit 3 Quiz"


def test_cross_school_isolation(client, db, years):
    """School A's teacher can neither see nor cancel a school B test."""
    a, b = years.a, years.b
    make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)
    make_timetable(db, b.school, b.year, b.grade, b.section, b.subject, b.teacher)

    b_row = make_slip_test(
        db, b.school, b.teacher, b.grade, b.section, b.subject, b.year,
    )
    make_slip_test(
        db, a.school, a.teacher, a.grade, a.section, a.subject, a.year,
    )

    h_a = auth(db, a.teacher_user)
    h_b = auth(db, b.teacher_user)

    # Teacher A: B's row is a 404, never a 403 that would confirm it exists.
    assert client.get(f"{TEACHER}/{b_row.id}", headers=h_a).status_code == 404
    assert client.put(
        f"{TEACHER}/{b_row.id}", json={"title": "x"}, headers=h_a
    ).status_code == 404
    assert client.post(f"{TEACHER}/{b_row.id}/cancel", headers=h_a).status_code == 404

    listed = client.get(f"{TEACHER}", headers=h_a).json()
    assert listed["total"] == 1
    assert listed["items"][0]["school_id"] == a.school.id

    # Teacher B still sees exactly their own.
    assert client.get(f"{TEACHER}", headers=h_b).json()["total"] == 1

    db.refresh(b_row)
    assert b_row.status == "scheduled"


def test_student_cannot_see_another_classs_slip_test(client, db, years):
    a = years.a
    a_row = make_slip_test(
        db, a.school, a.teacher, a.grade, a.section, a.subject, a.year,
    )

    # A second section in school A with its own student.
    section_b = make_section(db, a.grade, name="B")
    intruder_user = make_user(db, a.school, role="STUDENT")
    intruder = make_student(db, a.school, user=intruder_user)
    make_enrollment(db, intruder, a.year, section_b)

    h = auth(db, intruder_user)

    assert client.get(f"{STUDENT}/{a_row.id}", headers=h).status_code == 404
    listing = client.get(f"{STUDENT}", params={"filter": "all"}, headers=h).json()
    assert listing["total"] == 0
    assert all(item["id"] != a_row.id for item in listing["items"])


def test_student_sees_only_own_class(client, db, years):
    a = years.a
    mine = make_slip_test(
        db, a.school, a.teacher, a.grade, a.section, a.subject, a.year,
    )
    section_b = make_section(db, a.grade, name="B")
    theirs = make_slip_test(
        db, a.school, a.teacher, a.grade, section_b, a.subject, a.year,
    )

    h = auth(db, a.student_user)
    listing = client.get(f"{STUDENT}", params={"filter": "all"}, headers=h).json()

    ids = [item["id"] for item in listing["items"]]
    assert mine.id in ids
    assert theirs.id not in ids


def test_student_is_read_only(client, db, assigned):
    h = auth(db, assigned.student_user)
    row = make_slip_test(
        db, assigned.school, assigned.teacher, assigned.grade, assigned.section,
        assigned.subject, assigned.year,
    )

    assert client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).status_code == 403
    assert client.put(
        f"{TEACHER}/{row.id}", json={"title": "nope"}, headers=h
    ).status_code == 403
    assert client.post(f"{TEACHER}/{row.id}/cancel", headers=h).status_code == 403
    assert client.get(f"{STUDENT}/{row.id}", headers=h).status_code == 200


def test_principal_and_super_admin_have_no_slip_test_api(client, db, years):
    """Slip tests are strictly between teacher and student."""
    h_principal = auth(db, years.a.principal)
    h_super = auth(db, years.superadmin)

    for h in (h_principal, h_super):
        assert client.get(f"{TEACHER}/classes", headers=h).status_code == 403
        assert client.get(f"{TEACHER}", headers=h).status_code == 403
        assert client.post(
            f"{TEACHER}", json=create_payload(years.a), headers=h
        ).status_code == 403
        assert client.get(f"{STUDENT}", headers=h).status_code == 403


def test_teacher_cannot_use_student_endpoints(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    assert client.get(f"{STUDENT}", headers=h).status_code == 403


# ---------------------------------------------------------------------------
# 2. Validation
# ---------------------------------------------------------------------------


def test_valid_create_succeeds(client, db, assigned):
    h = auth(db, assigned.teacher_user)

    res = client.post(
        f"{TEACHER}",
        json=create_payload(assigned, start_time="09:30:00", duration_minutes=30),
        headers=h,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "scheduled"
    assert body["is_past"] is False
    assert body["subject_name"] == assigned.subject.name
    assert body["teacher_name"] == assigned.teacher_user.display_name
    assert db.query(SlipTest).count() == 1


@pytest.mark.parametrize(
    "override, expected",
    [
        ({"title": ""}, 422),
        ({"title": "   "}, 400),
        ({"title": "x" * 151}, 422),
        ({"max_marks": 0}, 422),
        ({"max_marks": -5}, 422),
        ({"max_marks": 1001}, 422),
        ({"description": "y" * 1001}, 422),
        ({"duration_minutes": 0}, 422),
        ({"duration_minutes": 601}, 422),
    ],
)
def test_field_bounds(client, db, assigned, override, expected):
    h = auth(db, assigned.teacher_user)
    res = client.post(f"{TEACHER}", json=create_payload(assigned, **override), headers=h)
    assert res.status_code == expected
    assert db.query(SlipTest).count() == 0


def test_past_date_is_rejected_but_today_is_allowed(client, db, assigned):
    h = auth(db, assigned.teacher_user)

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    res = client.post(
        f"{TEACHER}", json=create_payload(assigned, scheduled_date=yesterday), headers=h
    )
    assert res.status_code == 400
    assert "past" in res.json()["detail"].lower()

    today = date.today().isoformat()
    if assigned.year.start_date <= date.today() <= assigned.year.end_date:
        ok = client.post(
            f"{TEACHER}", json=create_payload(assigned, scheduled_date=today), headers=h
        )
        assert ok.status_code == 201


def test_date_outside_academic_year_is_rejected(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    outside = (assigned.year.end_date + timedelta(days=10)).isoformat()

    res = client.post(
        f"{TEACHER}", json=create_payload(assigned, scheduled_date=outside), headers=h
    )
    assert res.status_code == 400
    assert "academic year" in res.json()["detail"].lower()
    assert db.query(SlipTest).count() == 0


def test_closed_academic_year_is_rejected(client, db, assigned):
    from tests.factories import make_academic_year

    closed = make_academic_year(
        db,
        assigned.school,
        name="2020-2021",
        start=date(2020, 4, 1),
        end=date(2021, 3, 31),
        is_current=False,
        status="CLOSED",
    )
    h = auth(db, assigned.teacher_user)

    res = client.post(
        f"{TEACHER}",
        json=create_payload(assigned, academic_year_id=closed.id,
                            scheduled_date="2020-09-01"),
        headers=h,
    )
    assert res.status_code == 400
    assert "active academic year" in res.json()["detail"].lower()
    assert db.query(SlipTest).count() == 0


def test_html_is_stripped_from_text_fields(client, db, assigned):
    h = auth(db, assigned.teacher_user)

    res = client.post(
        f"{TEACHER}",
        json=create_payload(
            assigned,
            title="<script>alert(1)</script>Unit 3",
            description="<b>Chapter</b> 5 <img src=x onerror=alert(1)>",
        ),
        headers=h,
    )
    assert res.status_code == 201
    body = res.json()
    assert "<" not in body["title"] and "script" not in body["title"].lower()
    assert "<" not in body["description"] and "onerror" not in body["description"]
    assert "Chapter" in body["description"]


def test_duplicate_on_same_day_only_warns(client, db, assigned):
    h = auth(db, assigned.teacher_user)

    first = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h)
    assert first.status_code == 201
    assert first.json()["duplicate_warning"] is None

    second = client.post(
        f"{TEACHER}",
        json=create_payload(assigned, title="Unit 3 Quiz (revision)"),
        headers=h,
    )
    assert second.status_code == 201  # warn but allow
    assert second.json()["duplicate_warning"] is not None
    assert db.query(SlipTest).count() == 2


def test_teacher_class_cards_reflect_assignments_and_counts(client, db, assigned):
    h = auth(db, assigned.teacher_user)

    cards = client.get(f"{TEACHER}/classes", headers=h).json()
    assert cards["total"] == 1
    card = cards["items"][0]
    assert card["upcoming_count"] == 0
    assert card["subject_name"] == assigned.subject.name
    assert assigned.subject.name in card["display_name"]

    make_slip_test(
        db, assigned.school, assigned.teacher, assigned.grade, assigned.section,
        assigned.subject, assigned.year,
    )
    cards = client.get(f"{TEACHER}/classes", headers=h).json()
    assert cards["items"][0]["upcoming_count"] == 1
    assert cards["items"][0]["total_count"] == 1


def test_teacher_class_cards_empty_without_assignments(client, db, school_a):
    h = auth(db, school_a.teacher_user)
    assert client.get(f"{TEACHER}/classes", headers=h).json() == {"total": 0, "items": []}


# ---------------------------------------------------------------------------
# 3. Notifications
# ---------------------------------------------------------------------------


def test_create_notifies_every_enrolled_active_student(client, db, assigned):
    second_user = make_user(db, assigned.school, role="STUDENT")
    second = make_student(db, assigned.school, user=second_user)
    make_enrollment(db, second, assigned.year, assigned.section)

    h = auth(db, assigned.teacher_user)
    res = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h)
    assert res.status_code == 201
    slip = res.json()

    for student_user in (assigned.student_user, second_user):
        notes = slip_notifications(db, student_user)
        assert len(notes) == 1
        note = notes[0]
        assert note.notification_type == "SLIP_TEST"
        assert note.target_class_id == assigned.section.id
        assert note.reference_id == slip["id"]          # deep link target
        assert note.school_id == assigned.school.id
        assert note.sender_role == "TEACHER"
        assert assigned.subject.name in note.message
        assert "20 marks" in note.message
        assert note.is_read is False


def test_create_does_not_notify_other_classes_or_schools(client, db, years):
    a, b = years.a, years.b
    make_timetable(db, a.school, a.year, a.grade, a.section, a.subject, a.teacher)

    other_section = make_section(db, a.grade, name="B")
    outsider_user = make_user(db, a.school, role="STUDENT")
    outsider = make_student(db, a.school, user=outsider_user)
    make_enrollment(db, outsider, a.year, other_section)

    h = auth(db, a.teacher_user)
    assert client.post(f"{TEACHER}", json=create_payload(a), headers=h).status_code == 201

    assert slip_notifications(db, outsider_user) == []
    # School B's student gets nothing either.
    assert slip_notifications(db, b.student_user) == []


def test_inactive_students_are_not_notified(client, db, assigned):
    inactive_user = make_user(db, assigned.school, role="STUDENT", is_active="INACTIVE")
    inactive = make_student(db, assigned.school, user=inactive_user,
                            student_status="ACTIVE")
    make_enrollment(db, inactive, assigned.year, assigned.section)

    left_school_user = make_user(db, assigned.school, role="STUDENT")
    left_school = make_student(db, assigned.school, user=left_school_user,
                               student_status="INACTIVE")
    make_enrollment(db, left_school, assigned.year, assigned.section)

    h = auth(db, assigned.teacher_user)
    assert client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).status_code == 201

    assert slip_notifications(db, inactive_user) == []
    assert slip_notifications(db, left_school_user) == []
    assert len(slip_notifications(db, assigned.student_user)) == 1


def test_empty_class_notifies_nobody_and_still_succeeds(client, db, years):
    """Teacher assigned to a class with no students: create works, no notices."""
    a = years.a
    empty_section = make_section(db, a.grade, name="Empty")
    make_timetable(
        db, a.school, a.year, a.grade, empty_section, a.subject, a.teacher,
    )
    # `world` already enrolled the only student in `a.section`, so the brand-new
    # section is genuinely empty - no extra enrollment needed.

    h = auth(db, a.teacher_user)
    res = client.post(
        f"{TEACHER}",
        json=create_payload(a, section_id=empty_section.id),
        headers=h,
    )
    assert res.status_code == 201
    assert slip_notifications(db, a.student_user) == []


def test_slip_test_and_notifications_roll_back_together(client, db, assigned, monkeypatch):
    """If the fan-out fails, the slip test must not survive either."""
    from app.services import slip_test as service_module

    def boom(*_args, **_kwargs):
        raise RuntimeError("notification fan-out exploded")

    monkeypatch.setattr(service_module, "_fan_out", boom)

    h = auth(db, assigned.teacher_user)
    # `raise_server_exceptions=True` re-raises out of the ASGI app, which is
    # exactly what lets us assert the rollback happened.
    with pytest.raises(RuntimeError):
        client.post(f"{TEACHER}", json=create_payload(assigned), headers=h)

    assert db.query(SlipTest).count() == 0
    assert slip_notifications(db, assigned.student_user) == []


def test_edit_of_student_visible_fields_notifies(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()

    res = client.put(
        f"{TEACHER}/{created['id']}",
        json={"scheduled_date": IN_TWO_DAYS, "max_marks": 30},
        headers=h,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["scheduled_date"] == IN_TWO_DAYS
    assert body["max_marks"] == 30

    notes = slip_notifications(db, assigned.student_user)
    assert len(notes) == 2
    assert notes[0].title == "Slip test updated"
    assert "30 marks" in notes[0].message
    assert notes[0].reference_id == created["id"]


def test_title_only_edit_does_not_notify(client, db, assigned):
    """Renaming a test is not news; moving it is."""
    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()

    res = client.put(
        f"{TEACHER}/{created['id']}", json={"title": "Unit 3 Quiz (revised)"}, headers=h
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Unit 3 Quiz (revised)"
    assert len(slip_notifications(db, assigned.student_user)) == 1


def test_edit_rolls_back_when_notification_fails(client, db, assigned, monkeypatch):
    from app.services import slip_test as service_module

    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()

    def boom(*_args, **_kwargs):
        raise RuntimeError("fan-out exploded")

    monkeypatch.setattr(service_module, "_fan_out", boom)
    with pytest.raises(RuntimeError):
        client.put(f"{TEACHER}/{created['id']}", json={"max_marks": 40}, headers=h)

    row = db.query(SlipTest).filter(SlipTest.id == created["id"]).first()
    db.refresh(row)
    assert row.max_marks == 20  # the failed edit did not stick
    # ...and no second notice was left behind either.
    assert len(slip_notifications(db, assigned.student_user)) == 1


# ---------------------------------------------------------------------------
# 4. Soft cancel
# ---------------------------------------------------------------------------


def test_cancel_is_soft_and_notifies(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()

    res = client.post(f"{TEACHER}/{created['id']}/cancel", headers=h)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    # Row still there - never hard deleted.
    row = db.query(SlipTest).filter(SlipTest.id == created["id"]).first()
    assert row is not None

    notes = slip_notifications(db, assigned.student_user)
    assert notes[0].title == "Slip test cancelled"
    assert "cancelled" in notes[0].message.lower()
    assert notes[0].reference_id == created["id"]


def test_student_still_sees_cancelled_test_marked(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()
    assert client.post(f"{TEACHER}/{created['id']}/cancel", headers=h).status_code == 200

    sh = auth(db, assigned.student_user)
    detail = client.get(f"{STUDENT}/{created['id']}", headers=sh)
    assert detail.status_code == 200
    assert detail.json()["status"] == "cancelled"

    upcoming = client.get(f"{STUDENT}", params={"filter": "upcoming"}, headers=sh).json()
    assert upcoming["total"] == 1  # cancelled tests stay visible


def test_editing_a_cancelled_test_is_a_clear_409(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()
    client.post(f"{TEACHER}/{created['id']}/cancel", headers=h)

    res = client.put(
        f"{TEACHER}/{created['id']}", json={"max_marks": 25}, headers=h
    )
    assert res.status_code == 409
    assert "cancelled" in res.json()["detail"].lower()

    row = db.query(SlipTest).filter(SlipTest.id == created["id"]).first()
    db.refresh(row)
    assert row.max_marks == 20


def test_cancel_twice_is_idempotent_without_respam(client, db, assigned):
    h = auth(db, assigned.teacher_user)
    created = client.post(f"{TEACHER}", json=create_payload(assigned), headers=h).json()

    assert client.post(f"{TEACHER}/{created['id']}/cancel", headers=h).status_code == 200
    assert client.post(f"{TEACHER}/{created['id']}/cancel", headers=h).status_code == 200

    titles = [n.title for n in slip_notifications(db, assigned.student_user)]
    assert titles.count("Slip test cancelled") == 1


# ---------------------------------------------------------------------------
# 5. Derived upcoming / past filters
# ---------------------------------------------------------------------------


def test_student_filters_derive_from_the_date(client, db, assigned):
    upcoming_row = make_slip_test(
        db, assigned.school, assigned.teacher, assigned.grade, assigned.section,
        assigned.subject, assigned.year,
    )
    past_row = make_slip_test(
        db, assigned.school, assigned.teacher, assigned.grade, assigned.section,
        assigned.subject, assigned.year,
        scheduled_date=date.today() - timedelta(days=1),
    )
    today_row = make_slip_test(
        db, assigned.school, assigned.teacher, assigned.grade, assigned.section,
        assigned.subject, assigned.year,
        scheduled_date=date.today(),
    )

    h = auth(db, assigned.student_user)

    up = client.get(f"{STUDENT}", params={"filter": "upcoming"}, headers=h).json()
    up_ids = {i["id"] for i in up["items"]}
    assert up_ids == {upcoming_row.id, today_row.id}
    assert past_row.id not in up_ids

    past = client.get(f"{STUDENT}", params={"filter": "past"}, headers=h).json()
    assert {i["id"] for i in past["items"]} == {past_row.id}

    every = client.get(f"{STUDENT}", params={"filter": "all"}, headers=h).json()
    assert {i["id"] for i in every["items"]} == {upcoming_row.id, past_row.id, today_row.id}

    detail = client.get(f"{STUDENT}/{past_row.id}", headers=h).json()
    assert detail["is_past"] is True
    assert client.get(f"{STUDENT}/{upcoming_row.id}", headers=h).json()["is_past"] is False


def test_invalid_filter_is_rejected(client, db, assigned):
    h = auth(db, assigned.student_user)
    assert client.get(f"{STUDENT}", params={"filter": "nonsense"}, headers=h).status_code == 422


def test_student_pagination_window_across_sections(client, db, assigned):
    """skip/limit are applied once to the merged, sorted list.

    Regression guard: slicing inside the per-section loop paginated each section
    separately and silently dropped rows the caller had asked for.
    """
    a = assigned
    made = [
        make_slip_test(
            db, a.school, a.teacher, a.grade, a.section, a.subject, a.year,
            scheduled_date=date.today() + timedelta(days=index + 1),
            title=f"Quiz {index + 1}",
        )
        for index in range(6)
    ]
    h = auth(db, a.student_user)

    every = client.get(f"{STUDENT}", params={"filter": "all", "limit": 100}, headers=h).json()
    assert every["total"] == 6
    expected_ids = [row.id for row in made]

    page = client.get(
        f"{STUDENT}", params={"filter": "all", "skip": 2, "limit": 3}, headers=h
    ).json()
    assert page["total"] == 6
    assert [i["id"] for i in page["items"]] == expected_ids[2:5]

    tail = client.get(
        f"{STUDENT}", params={"filter": "all", "skip": 5, "limit": 3}, headers=h
    ).json()
    assert [i["id"] for i in tail["items"]] == expected_ids[5:]


def test_mid_year_transfer_shows_only_the_current_class(client, db, assigned):
    """Re-enrolled into 10-B mid-year: 10-A's tests disappear for this student."""
    a = assigned
    a_row = make_slip_test(
        db, a.school, a.teacher, a.grade, a.section, a.subject, a.year,
    )
    new_section = make_section(db, a.grade, name="B")
    new_row = make_slip_test(
        db, a.school, a.teacher, a.grade, new_section, a.subject, a.year,
    )

    # Transfer: the unique (student, year) enrollment is replaced.
    from app.models.student_enrollment import StudentEnrollment

    db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == a.student.id,
        StudentEnrollment.academic_year_id == a.year.id,
    ).delete()
    db.flush()
    make_enrollment(db, a.student, a.year, new_section)

    h = auth(db, a.student_user)
    ids = {
        i["id"]
        for i in client.get(f"{STUDENT}", params={"filter": "all"}, headers=h).json()["items"]
    }
    assert new_row.id in ids
    assert a_row.id not in ids
    assert client.get(f"{STUDENT}/{a_row.id}", headers=h).status_code == 404