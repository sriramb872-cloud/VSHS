"""Web Push (VAPID) tests.

Covers recipient resolution (mirroring ``CRUDNotification._visible_query``,
never wider), subscription management (upsert / reassignment / cap /
ownership), dispatch behaviour (404/410 cleanup, best-effort failures,
``push=False``) and tenant isolation (school B never receives school A's
pushes).
"""

from __future__ import annotations

import hashlib
import json

import pywebpush
import pytest

from app.core.config import settings
from app.crud.notification import notification as crud_notification
from app.models.push_subscription import PushSubscription
from app.services import push as push_module
from tests.factories import (
    make_enrollment,
    make_notification,
    make_section,
    make_student,
    make_user,
)
from tests.helpers import auth

PREFIX = "/api/v1"


def _endpoint_hash(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _add_subscription(db, user, endpoint="https://push.example.com/abc", **overrides):
    row = PushSubscription(
        user_id=user.id,
        endpoint=endpoint,
        endpoint_hash=_endpoint_hash(endpoint),
        p256dh=overrides.pop("p256dh", "p256dh-1"),
        auth=overrides.pop("auth", "auth-1"),
        **overrides,
    )
    db.add(row)
    db.commit()
    return row


@pytest.fixture
def webpush_sent(db, monkeypatch):
    """Push enabled, inline dispatch, mocked ``pywebpush.webpush``.

    Returns the list of captured calls so tests can assert on payloads.
    """
    monkeypatch.setattr(settings, "PUSH_ENABLED", True)
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "fake-public-key")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "fake-private-key")
    monkeypatch.setattr(push_module, "DISPATCH_INLINE", True)

    sent = []

    def fake_webpush(subscription_info, data=None, **kwargs):
        sent.append(
            {
                "subscription_info": subscription_info,
                "data": json.loads(data) if data else None,
                "kwargs": kwargs,
            }
        )
        return "ok"

    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)
    return sent


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = f"status {status_code}"


def _failing_webpush(status_code):
    def fake_webpush(subscription_info, data=None, **kwargs):
        raise pywebpush.WebPushException("push failed", response=_FakeResponse(status_code))

    return fake_webpush


# ---------------------------------------------------------------------------
# Public-key endpoint
# ---------------------------------------------------------------------------


def test_public_key_disabled_when_keys_missing(client, db, world, monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", None)
    monkeypatch.setattr(settings, "PUSH_ENABLED", False)

    resp = client.get(
        f"{PREFIX}/notifications/push/public-key",
        headers=auth(db, world.a.principal),
    )
    assert resp.status_code == 200
    assert resp.json() == {"public_key": "", "enabled": False}


def test_public_key_enabled_when_keys_configured(client, db, world, monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "fake-public")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "fake-private")
    monkeypatch.setattr(settings, "PUSH_ENABLED", True)

    resp = client.get(
        f"{PREFIX}/notifications/push/public-key",
        headers=auth(db, world.a.principal),
    )
    assert resp.status_code == 200
    assert resp.json() == {"public_key": "fake-public", "enabled": True}


# ---------------------------------------------------------------------------
# Recipient resolution
# ---------------------------------------------------------------------------


def test_public_recipients(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="PUBLIC", category="PUBLIC",
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    # students + teachers + principals of school A, sender (principal) excluded
    assert ids == {world.a.student_user.id, world.a.teacher_user.id}


def test_public_excludes_inactive_users(db, world):
    inactive = make_user(
        db, world.a.school, role="TEACHER", display_name="Inactive Teacher",
        is_active="INACTIVE",
    )
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="PUBLIC", category="PUBLIC",
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert inactive.id not in ids


def test_staff_only_recipients(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="STAFF_ONLY", category="STAFF",
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    # teachers + principals only; the student is not staff, the sender
    # (principal) is excluded
    assert ids == {world.a.teacher_user.id}


def test_class_only_recipients(db, world):
    # A second section in school A with its own student: must NOT receive.
    other_user = make_user(db, world.a.school, role="STUDENT", display_name="Other Student")
    other_student = make_student(db, world.a.school, user=other_user)
    other_section = make_section(db, world.a.grade, name="B")
    make_enrollment(db, other_student, world.a.year, other_section)

    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="CLASS_ONLY", category="CLASS",
        target_class_id=world.a.section.id,
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert ids == {world.a.student_user.id}
    assert other_user.id not in ids


def test_only_for_class_recipients(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="ONLY_FOR_CLASS", category="CLASS_TEACHER",
        target_class_id=world.a.section.id,
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert ids == {world.a.student_user.id}


def test_only_for_student_with_user_id(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="ONLY_FOR_STUDENT", category="CLASS_TEACHER",
        target_student_id=world.a.student.id, user_id=world.a.student_user.id,
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert ids == {world.a.student_user.id}


def test_only_for_student_without_user_id(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="ONLY_FOR_STUDENT", category="CLASS_TEACHER",
        target_student_id=world.a.student.id,
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert ids == {world.a.student_user.id}


def test_direct_user_id_goes_only_to_that_user(db, world):
    """Quirk: STAFF_ONLY rows with user_id are shown school-wide in-app but
    must be pushed ONLY to the addressed user."""
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="STAFF_ONLY", category="STAFF",
        user_id=world.a.teacher_user.id,
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert ids == {world.a.teacher_user.id}


def test_sender_excluded(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.teacher_user,
        notification_type="STAFF_ONLY", category="STAFF",
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert world.a.teacher_user.id not in ids
    assert ids == {world.a.principal.id}


def test_other_school_never_receives(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="PUBLIC", category="PUBLIC",
    )
    ids = {u.id for u in push_module.resolve_recipients(db, n)}
    assert world.b.student_user.id not in ids
    assert world.b.teacher_user.id not in ids
    assert world.b.principal.id not in ids


def test_super_admin_excluded_from_school_wide_but_gets_direct(db, world):
    admin = make_user(db, world.a.school, role="SUPER_ADMIN", display_name="Admin With School")

    school_wide = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="PUBLIC", category="PUBLIC",
    )
    ids = {u.id for u in push_module.resolve_recipients(db, school_wide)}
    assert admin.id not in ids

    direct = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="STAFF_ONLY", category="STAFF", user_id=admin.id,
    )
    ids = {u.id for u in push_module.resolve_recipients(db, direct)}
    assert ids == {admin.id}


def test_unknown_type_fails_closed(db, world):
    n = make_notification(
        db, world.a.school, sender=world.a.principal,
        notification_type="SLIP_TEST", category="SLIP_TEST",
    )
    assert push_module.resolve_recipients(db, n) == []


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe API
# ---------------------------------------------------------------------------


def _push_enabled(monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "fake-public-key")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "fake-private-key")
    monkeypatch.setattr(settings, "PUSH_ENABLED", True)


def _subscribe(client, db, user, endpoint, **overrides):
    return client.post(
        f"{PREFIX}/notifications/push/subscribe",
        headers=auth(db, user),
        json={"endpoint": endpoint, "keys": {"p256dh": "p256dh", "auth": "auth"}, **overrides},
    )


def test_subscribe_creates_subscription(client, db, world, monkeypatch):
    _push_enabled(monkeypatch)
    resp = _subscribe(client, db, world.a.student_user, "https://push.example.com/abc")
    assert resp.status_code == 201, resp.text

    row = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == world.a.student_user.id)
        .first()
    )
    assert row is not None
    assert row.endpoint == "https://push.example.com/abc"
    assert row.endpoint_hash == _endpoint_hash("https://push.example.com/abc")


def test_subscribe_requires_https(client, db, world, monkeypatch):
    _push_enabled(monkeypatch)
    resp = _subscribe(client, db, world.a.student_user, "http://push.example.com/abc")
    assert resp.status_code == 400


def test_subscribe_disabled_returns_503(client, db, world, monkeypatch):
    monkeypatch.setattr(settings, "PUSH_ENABLED", False)
    resp = _subscribe(client, db, world.a.student_user, "https://push.example.com/abc")
    assert resp.status_code == 503


def test_subscribe_upserts_for_same_user(client, db, world, monkeypatch):
    _push_enabled(monkeypatch)
    endpoint = "https://push.example.com/abc"
    assert _subscribe(client, db, world.a.student_user, endpoint).status_code == 201
    resp = _subscribe(client, db, world.a.student_user, endpoint)
    assert resp.status_code == 201, resp.text

    rows = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == _endpoint_hash(endpoint))
        .all()
    )
    assert len(rows) == 1
    assert rows[0].user_id == world.a.student_user.id


def test_subscribe_reassigns_shared_device(client, db, world, monkeypatch):
    """Same endpoint, different logged-in user: reassign, don't duplicate."""
    _push_enabled(monkeypatch)
    endpoint = "https://push.example.com/shared"
    assert _subscribe(client, db, world.a.student_user, endpoint).status_code == 201
    resp = _subscribe(client, db, world.a.teacher_user, endpoint)
    assert resp.status_code == 201, resp.text

    rows = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == _endpoint_hash(endpoint))
        .all()
    )
    assert len(rows) == 1
    assert rows[0].user_id == world.a.teacher_user.id


def test_subscribe_caps_at_ten_per_user(client, db, world, monkeypatch):
    _push_enabled(monkeypatch)
    user = world.a.student_user
    for i in range(10):
        _add_subscription(db, user, endpoint=f"https://push.example.com/{i}")

    resp = _subscribe(client, db, user, "https://push.example.com/extra")
    assert resp.status_code == 201, resp.text

    rows = (
        db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
    )
    assert len(rows) == 10
    # The oldest subscription was deleted to make room.
    assert all(r.endpoint != "https://push.example.com/0" for r in rows)


def test_unsubscribe_ownership_and_idempotency(client, db, world, monkeypatch):
    _push_enabled(monkeypatch)
    endpoint = "https://push.example.com/abc"
    _add_subscription(db, world.a.student_user, endpoint=endpoint)

    # A different user cannot delete someone else's subscription.
    resp = client.post(
        f"{PREFIX}/notifications/push/unsubscribe",
        headers=auth(db, world.a.teacher_user),
        json={"endpoint": endpoint},
    )
    assert resp.status_code == 200
    assert (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == _endpoint_hash(endpoint))
        .count()
        == 1
    )

    # The owner can, and a second call is a no-op success.
    resp = client.post(
        f"{PREFIX}/notifications/push/unsubscribe",
        headers=auth(db, world.a.student_user),
        json={"endpoint": endpoint},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "unsubscribed"}
    assert (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == _endpoint_hash(endpoint))
        .count()
        == 0
    )

    resp = client.post(
        f"{PREFIX}/notifications/push/unsubscribe",
        headers=auth(db, world.a.student_user),
        json={"endpoint": endpoint},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_dispatch_sends_to_recipients(db, world, webpush_sent):
    sub = _add_subscription(db, world.a.student_user)
    n = crud_notification.create(
        db,
        title="Hello",
        message="Body text",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    assert len(webpush_sent) == 1
    sent = webpush_sent[0]
    assert sent["subscription_info"]["endpoint"] == sub.endpoint
    assert sent["subscription_info"]["keys"] == {"p256dh": "p256dh-1", "auth": "auth-1"}
    assert sent["data"]["title"] == "Hello"
    assert sent["data"]["body"] == "Body text"
    assert sent["data"]["url"] == "/student/notifications"
    assert sent["data"]["notification_id"] == n.id
    assert sent["data"]["tag"] == f"n-{n.id}"

    db.refresh(sub)
    assert sub.last_used_at is not None


def test_dispatch_body_truncated_to_140(db, world, webpush_sent):
    _add_subscription(db, world.a.student_user)
    crud_notification.create(
        db,
        title="Long",
        message="x" * 200,
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    assert len(webpush_sent) == 1
    body = webpush_sent[0]["data"]["body"]
    assert len(body) == 140
    assert body.endswith("...")


def test_dispatch_410_deletes_subscription(db, world, webpush_sent, monkeypatch):
    sub = _add_subscription(db, world.a.student_user)
    endpoint_hash = sub.endpoint_hash
    monkeypatch.setattr(pywebpush, "webpush", _failing_webpush(410))

    crud_notification.create(
        db,
        title="Gone",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    assert webpush_sent == []
    db.expire_all()
    assert (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == endpoint_hash)
        .first()
        is None
    )


def test_dispatch_404_deletes_subscription(db, world, webpush_sent, monkeypatch):
    sub = _add_subscription(db, world.a.student_user)
    endpoint_hash = sub.endpoint_hash
    monkeypatch.setattr(pywebpush, "webpush", _failing_webpush(404))

    crud_notification.create(
        db,
        title="Gone",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    db.expire_all()
    assert (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == endpoint_hash)
        .first()
        is None
    )


def test_dispatch_500_keeps_subscription(db, world, webpush_sent, monkeypatch):
    sub = _add_subscription(db, world.a.student_user)
    monkeypatch.setattr(pywebpush, "webpush", _failing_webpush(500))

    crud_notification.create(
        db,
        title="Error",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    db.expire_all()
    assert db.query(PushSubscription).filter(PushSubscription.id == sub.id).first() is not None


def test_dispatch_generic_exception_keeps_subscription(db, world, webpush_sent, monkeypatch):
    sub = _add_subscription(db, world.a.student_user)

    def boom(subscription_info, data=None, **kwargs):
        raise RuntimeError("connection exploded")

    monkeypatch.setattr(pywebpush, "webpush", boom)

    crud_notification.create(
        db,
        title="Error",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    db.expire_all()
    assert db.query(PushSubscription).filter(PushSubscription.id == sub.id).first() is not None


def test_push_failure_does_not_break_create(db, world, monkeypatch):
    _add_subscription(db, world.a.student_user)
    monkeypatch.setattr(settings, "PUSH_ENABLED", True)
    monkeypatch.setattr(push_module, "DISPATCH_INLINE", True)

    def boom(subscription_info, data=None, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pywebpush, "webpush", boom)

    n = crud_notification.create(
        db,
        title="Still created",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    assert n.id is not None


def test_push_false_sends_nothing(db, world, webpush_sent):
    _add_subscription(db, world.a.student_user)
    crud_notification.create(
        db,
        title="No push",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
        push=False,
    )
    assert webpush_sent == []


def test_dispatch_noop_when_push_disabled(db, world, monkeypatch):
    _add_subscription(db, world.a.student_user)
    monkeypatch.setattr(settings, "PUSH_ENABLED", False)

    def boom(subscription_info, data=None, **kwargs):  # pragma: no cover
        raise AssertionError("webpush must not be called when push is disabled")

    monkeypatch.setattr(pywebpush, "webpush", boom)

    n = crud_notification.create(
        db,
        title="No push",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    assert n.id is not None


def test_dispatch_respects_tenant_isolation(db, world, webpush_sent):
    # A school-B device must never receive a school-A notification.
    _add_subscription(db, world.b.student_user)
    crud_notification.create(
        db,
        title="School A only",
        message="Body",
        notification_type="PUBLIC",
        sender_id=world.a.principal.id,
        sender_role="PRINCIPAL",
        school_id=world.a.school.id,
        category="PUBLIC",
    )
    assert webpush_sent == []
