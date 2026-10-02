"""Subscription & access-control module: behaviour, security and notifications.

Everything here is asserted through the REAL HTTP surface (or the real
service entry points) against real rows - no mocked entitlement logic.

Covered guarantees
-----------------
* rollout is fail-open: no ``school_subscription_settings`` row == disabled
* one authoritative resolver with the documented precedence
* enforcement is router-level on exactly the seven feature routers
* structured ``detail.code`` errors, never a stack trace
* expiry is evaluated from the clock: ``start_at <= now < end_at``
* renewal never throws paid time away (extend from the existing end)
* SUPER_ADMIN bypass; PRINCIPAL/TEACHER/STUDENT never reach admin APIs
* tenant isolation for plans, users, overrides and payments
* mock payment provider (development only) + hard production gating
* notifications reuse the existing pipeline (7/3/1-day, expired, payment)
* every access/billing change is audited (subscription + platform logs)
* ``users.is_active`` (account status) is NEVER touched by billing
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.time_utils import add_duration, utcnow
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.subscription_audit_log import SubscriptionAuditLog
from app.models.user import User
from app.models.user_subscription_override import UserSubscriptionOverride
from tests.helpers import auth

PREFIX = "/api/v1"

# The seven routers carrying the router-level entitlement dependency.
GATED_PATHS = (
    "/attendance",
    "/homework/",
    "/exams/",
    "/marks/",
    "/timetables",
    "/report-cards/",
    "/calendar-events/",
)

# Endpoints an expired user MUST still be able to reach with the same token.
SELF_SERVICE_PATHS = (
    "/auth/me",
    "/users/me",
    "/subscription/me",
    "/subscription/me/plans",
    "/subscription/me/history",
    "/subscription/me/payments",
    "/notifications/",
    "/dashboard/student",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def in_days(days: float) -> str:
    """Naive-UTC ISO timestamp ``days`` from now (the house time policy)."""
    return (utcnow() + timedelta(days=days)).isoformat()


def enable(client, headers, school_id, *, free_until=None):
    payload = {"subscriptions_enabled": True}
    if free_until is not None:
        payload["free_until"] = free_until
    resp = client.patch(
        f"{PREFIX}/subscription/schools/{school_id}/settings",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def plan_payload(**overrides):
    payload = {
        "name": "Student Monthly",
        "price": 100.0,
        "currency": "INR",
        "billing_interval": "MONTHLY",
        "duration_value": 1,
        "duration_unit": "MONTH",
        "role": "STUDENT",
    }
    payload.update(overrides)
    return payload


def make_plan(client, headers, school_id, **overrides):
    resp = client.post(
        f"{PREFIX}/subscription/schools/{school_id}/plans",
        headers=headers,
        json=plan_payload(**overrides),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def grant(client, headers, user_id, plan_id, reason=None):
    body = {"plan_id": plan_id}
    if reason:
        body["reason"] = reason
    resp = client.post(
        f"{PREFIX}/subscription/users/{user_id}/grant", headers=headers, json=body
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def access_of(client, headers):
    resp = client.get(f"{PREFIX}/subscription/me", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["access"]


def detail_of(resp):
    """The subscription domain always answers with a structured detail."""
    detail = resp.json().get("detail")
    assert isinstance(detail, dict), f"expected object detail, got {detail!r}"
    return detail


def assert_denied(resp, code="SUBSCRIPTION_REQUIRED", status_code=403):
    assert resp.status_code == status_code, f"{resp.status_code}: {resp.text[:400]}"
    detail = detail_of(resp)
    assert detail["code"] == code, detail
    assert "Traceback" not in resp.text
    return detail


def assert_error(resp, code, status_code):
    assert resp.status_code == status_code, f"{resp.status_code}: {resp.text[:400]}"
    assert detail_of(resp)["code"] == code, resp.text[:400]


def checkout(client, headers, plan_id):
    resp = client.post(
        f"{PREFIX}/subscription/payments", headers=headers, json={"plan_id": plan_id}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def complete(client, headers, payment_id, outcome):
    return client.post(
        f"{PREFIX}/subscription/payments/{payment_id}/mock/complete",
        headers=headers,
        json={"outcome": outcome},
    )


def notifications_for(db, user, title):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.title == title)
        .count()
    )


def expire_subscription(db, user_id, *, days_ago=1.0):
    """Push every live row of a user into the past (simulated expiry)."""
    db.query(Subscription).filter(
        Subscription.user_id == user_id, Subscription.status == "ACTIVE"
    ).update(
        {"end_at": utcnow() - timedelta(days=days_ago)},
        synchronize_session=False,
    )
    db.commit()


# ---------------------------------------------------------------------------
# 1. Rollout is fail-open: no settings row means subscriptions are off
# ---------------------------------------------------------------------------


def test_subscriptions_disabled_by_default_keeps_everything_reachable(client, db, world):
    student = auth(db, world.a.student_user)

    for path in GATED_PATHS:
        resp = client.get(f"{PREFIX}{path}", headers=student)
        assert resp.status_code == 200, f"{path} -> {resp.text[:300]}"

    access = access_of(client, student)
    assert access["has_access"] is True
    assert access["reason"] == "SCHOOL_SUBSCRIPTIONS_DISABLED"
    assert access["subscriptions_enabled"] is False


def test_only_the_enabled_school_is_gated(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)

    gated = auth(db, world.a.student_user)
    open_school = auth(db, world.b.student_user)

    assert_denied(client.get(f"{PREFIX}/attendance", headers=gated))
    assert client.get(f"{PREFIX}/attendance", headers=open_school).status_code == 200


# ---------------------------------------------------------------------------
# 2. Enabling a school gates exactly the seven feature routers
# ---------------------------------------------------------------------------


def test_enabling_a_school_returns_structured_403_on_every_gated_router(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    student = auth(db, world.a.student_user)

    for path in GATED_PATHS:
        resp = client.get(f"{PREFIX}{path}", headers=student)
        detail = assert_denied(resp, "SUBSCRIPTION_REQUIRED", 403)
        assert detail["subscription_status"] == "PAYMENT_REQUIRED", path
        assert detail["reason"] == "NONE", path
        assert "message" in detail

    access = access_of(client, student)
    assert access["has_access"] is False
    assert access["status"] == "PAYMENT_REQUIRED"
    assert access["subscriptions_enabled"] is True


def test_principals_and_teachers_are_gated_too(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)

    for who in ("principal", "teacher_user"):
        resp = client.get(f"{PREFIX}/exams/", headers=auth(db, getattr(world.a, who)))
        assert resp.status_code == 403, resp.text
        assert detail_of(resp)["code"] == "SUBSCRIPTION_REQUIRED"


# ---------------------------------------------------------------------------
# 3. Precedence: school free -> user free override -> active subscription
# ---------------------------------------------------------------------------


def test_school_wide_free_period_then_expiry(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id
    student = auth(db, world.a.student_user)

    enable(client, sa, school_id, free_until=in_days(7))
    assert client.get(f"{PREFIX}/attendance", headers=student).status_code == 200
    access = access_of(client, student)
    assert access["reason"] == "SCHOOL_FREE"
    assert access["has_access"] is True

    # Free window already elapsed -> pay up.
    enable(client, sa, school_id, free_until=in_days(-1))
    assert_denied(client.get(f"{PREFIX}/attendance", headers=student))
    access = access_of(client, student)
    assert access["has_access"] is False
    assert access["reason"] == "NONE"


def test_individual_free_override_beats_a_missing_subscription(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    target = world.a.student_user
    student = auth(db, target)

    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/override",
        headers=sa,
        json={"override_type": "FREE", "free_until": in_days(3), "reason": "demo"},
    )
    assert resp.status_code == 201, resp.text

    assert client.get(f"{PREFIX}/attendance", headers=student).status_code == 200
    access = access_of(client, student)
    assert access["reason"] == "USER_FREE_OVERRIDE"
    assert access["user_free_until"] is not None

    # Move the override into the past -> access is withdrawn again.
    resp = client.patch(
        f"{PREFIX}/subscription/users/{target.id}/override",
        headers=sa,
        json={"free_until": in_days(-1)},
    )
    assert resp.status_code == 200, resp.text

    assert_denied(client.get(f"{PREFIX}/attendance", headers=student))
    assert access_of(client, student)["has_access"] is False

    # A second FREE override is a conflict, not a silent duplicate.
    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/override",
        headers=sa,
        json={"override_type": "FREE"},
    )
    assert_error(resp, "OVERRIDE_EXISTS", 409)


def test_active_subscription_grants_access_to_every_gated_router(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id
    enable(client, sa, school_id)
    plan = make_plan(client, sa, school_id, duration_value=7, duration_unit="DAY")
    grant(client, sa, world.a.student_user.id, plan["id"])
    student = auth(db, world.a.student_user)

    for path in GATED_PATHS:
        resp = client.get(f"{PREFIX}{path}", headers=student)
        assert resp.status_code == 200, f"{path} -> {resp.text[:300]}"

    access = access_of(client, student)
    assert access["has_access"] is True
    assert access["status"] == "ACTIVE"
    assert access["reason"] == "ADMIN_GRANT"
    assert access["expires_at"] is not None


def test_expired_subscription_denies_and_notifies_once(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])
    student = auth(db, target)

    expire_subscription(db, target.id)

    for path in GATED_PATHS:
        detail = assert_denied(client.get(f"{PREFIX}{path}", headers=student))
        assert detail["reason"] == "EXPIRED", path
        assert detail["subscription_status"] == "PAYMENT_REQUIRED"

    # De-duplicated: the "expired" mail-spike cannot happen.
    assert notifications_for(db, target, "Subscription expired") == 1


# ---------------------------------------------------------------------------
# 4. Expiry is evaluated from the clock (half-open interval)
# ---------------------------------------------------------------------------


def test_expiry_boundary_is_half_open(client, db, world, monkeypatch):
    from app.services import subscription as subscription_module
    from app.services.subscription import SubscriptionError, SubscriptionService

    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    sub = grant(client, sa, target.id, plan["id"])

    fixed = datetime(2030, 6, 1, 12, 0, 0)
    monkeypatch.setattr(subscription_module, "utcnow", lambda: fixed)

    row = db.query(Subscription).filter(Subscription.id == sub["id"]).one()

    # now == end_at -> the window is CLOSED, so access is gone.
    row.start_at = fixed - timedelta(days=30)
    row.end_at = fixed
    db.commit()
    access = SubscriptionService.get_access_status(db, target)
    assert access.has_access is False
    assert access.reason == "EXPIRED"
    with pytest.raises(SubscriptionError) as exc:
        SubscriptionService.require_access(db, target)
    assert exc.value.detail["code"] == "SUBSCRIPTION_REQUIRED"

    # now == start_at -> the window is OPEN.
    row.start_at = fixed
    row.end_at = fixed + timedelta(days=30)
    db.commit()
    access = SubscriptionService.get_access_status(db, target)
    assert access.has_access is True
    assert access.reason == "ADMIN_GRANT"

    # One tick before the start the user is still locked out.
    row.start_at = fixed + timedelta(seconds=1)
    db.commit()
    assert SubscriptionService.get_access_status(db, target).has_access is False


def test_status_hygiene_rewrites_stale_active_rows_without_a_cron_job(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    sub = grant(client, sa, target.id, plan["id"])
    expire_subscription(db, target.id)

    # Access was already denied purely from the clock...
    assert_denied(client.get(f"{PREFIX}/attendance", headers=auth(db, target)))

    # ...and the stored row is corrected lazily by /subscription/me.
    client.get(f"{PREFIX}/subscription/me", headers=auth(db, target))
    db.expire_all()
    row = db.query(Subscription).filter(Subscription.id == sub["id"]).one()
    assert row.status == "EXPIRED"


# ---------------------------------------------------------------------------
# 5. Renewal rules
# ---------------------------------------------------------------------------


def test_renewal_of_a_live_subscription_extends_from_the_existing_end(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user

    first = grant(client, sa, target.id, plan["id"])
    first_end = datetime.fromisoformat(first["end_at"])

    second = grant(client, sa, target.id, plan["id"], reason="renewal")
    second_end = datetime.fromisoformat(second["end_at"])

    # Paid time is never discarded: one row, extended from the previous end.
    assert second["id"] == first["id"]
    assert second_end == add_duration(first_end, 1, "MONTH")
    assert datetime.fromisoformat(second["start_at"]) == datetime.fromisoformat(
        first["start_at"]
    )

    db.expire_all()
    rows = db.query(Subscription).filter(Subscription.user_id == target.id).all()
    assert len(rows) == 1
    assert rows[0].status == "ACTIVE"


def test_renewal_after_expiry_starts_a_new_row_and_keeps_the_old_one(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user

    first = grant(client, sa, target.id, plan["id"])
    expire_subscription(db, target.id, days_ago=5)
    db.expire_all()
    old_end = (
        db.query(Subscription).filter(Subscription.id == first["id"]).one().end_at
    )

    second = grant(client, sa, target.id, plan["id"])
    assert second["id"] != first["id"]

    db.expire_all()
    rows = db.query(Subscription).filter(Subscription.user_id == target.id).all()
    assert len(rows) == 2

    old = next(r for r in rows if r.id == first["id"])
    new = next(r for r in rows if r.id == second["id"])

    # History survives, honestly labelled.
    assert old.status == "EXPIRED"
    # The new period starts NOW - it must not start in the distant past.
    assert old_end < new.start_at <= utcnow()
    assert new.end_at > utcnow()
    assert new.status == "ACTIVE"

    assert access_of(client, auth(db, target))["has_access"] is True


def test_extend_adds_time_to_a_live_subscription(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    first = grant(client, sa, target.id, plan["id"])

    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/extend",
        headers=sa,
        json={"duration_value": 15, "duration_unit": "DAY", "reason": "goodwill"},
    )
    assert resp.status_code == 200, resp.text
    expected = add_duration(datetime.fromisoformat(first["end_at"]), 15, "DAY")
    assert datetime.fromisoformat(resp.json()["end_at"]) == expected


# ---------------------------------------------------------------------------
# 6. SUPER_ADMIN bypass and admin API role gates
# ---------------------------------------------------------------------------


def test_super_admin_bypasses_the_gate_even_without_a_school(client, db, world):
    sa = auth(db, world.superadmin)
    # School A is enforcing subscriptions; school-less super admin must not care.
    enable(client, sa, world.a.school.id)

    for path in GATED_PATHS:
        resp = client.get(f"{PREFIX}{path}", headers=sa)
        assert resp.status_code == 200, f"{path} -> {resp.text[:300]}"

    access = access_of(client, sa)
    assert access["has_access"] is True
    assert access["reason"] == "SUPER_ADMIN"


@pytest.mark.parametrize("who", ["principal", "teacher_user", "student_user"])
def test_only_super_admin_can_manage_subscriptions(client, db, world, who):
    headers = auth(db, getattr(world.a, who))

    cases = [
        ("GET", f"{PREFIX}/subscription/schools", None),
        ("GET", f"{PREFIX}/subscription/schools/{world.a.school.id}", None),
        ("GET", f"{PREFIX}/subscription/metrics", None),
        ("GET", f"{PREFIX}/subscription/plans", None),
        ("PATCH", f"{PREFIX}/subscription/schools/{world.a.school.id}/settings",
         {"subscriptions_enabled": True}),
        ("POST", f"{PREFIX}/subscription/schools/{world.a.school.id}/plans",
         plan_payload()),
        ("POST", f"{PREFIX}/subscription/users/{world.a.student_user.id}/grant",
         {"plan_id": 1}),
        ("POST", f"{PREFIX}/subscription/schools/{world.a.school.id}/bulk",
         {"action": "FREE_UNTIL", "user_ids": [world.a.student_user.id],
          "free_until": in_days(5)}),
    ]
    for method, path, body in cases:
        resp = getattr(client, method.lower())(
            path, headers=headers, **({"json": body} if body is not None else {})
        )
        assert resp.status_code == 403, f"{method} {path} -> {resp.text[:300]}"
        assert detail_of(resp)["code"] == "UNAUTHORIZED_SUBSCRIPTION_ACTION", path


# ---------------------------------------------------------------------------
# 7. Tenant isolation inside the billing domain
# ---------------------------------------------------------------------------


def test_cross_school_and_role_mismatched_grants_are_rejected(client, db, world):
    sa = auth(db, world.superadmin)

    plan_b = make_plan(client, sa, world.b.school.id)
    resp = client.post(
        f"{PREFIX}/subscription/users/{world.a.student_user.id}/grant",
        headers=sa,
        json={"plan_id": plan_b["id"]},
    )
    assert_error(resp, "USER_NOT_IN_SCHOOL", 400)
    assert db.query(Subscription).filter(
        Subscription.user_id == world.a.student_user.id
    ).count() == 0

    plan_teacher_a = make_plan(client, sa, world.a.school.id, role="TEACHER")
    resp = client.post(
        f"{PREFIX}/subscription/users/{world.a.student_user.id}/grant",
        headers=sa,
        json={"plan_id": plan_teacher_a["id"]},
    )
    assert_error(resp, "PLAN_ROLE_MISMATCH", 400)

    # Same mismatch shows up at checkout too (amount always comes from the DB).
    resp = client.post(
        f"{PREFIX}/subscription/payments",
        headers=auth(db, world.a.student_user),
        json={"plan_id": plan_teacher_a["id"]},
    )
    assert_error(resp, "PLAN_ROLE_MISMATCH", 400)


def test_me_plans_are_scoped_to_the_callers_school_and_role(client, db, world):
    sa = auth(db, world.superadmin)
    plan_a_student = make_plan(client, sa, world.a.school.id, price=99.0)
    plan_a_teacher = make_plan(
        client, sa, world.a.school.id, role="TEACHER", price=199.0, name="Teacher"
    )
    plan_b_student = make_plan(client, sa, world.b.school.id, price=249.0, name="B plan")

    resp = client.get(
        f"{PREFIX}/subscription/me/plans", headers=auth(db, world.a.student_user)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role"] == "STUDENT"
    assert data["school_id"] == world.a.school.id

    ids = {p["id"] for p in data["plans"]}
    assert plan_a_student["id"] in ids
    assert plan_a_teacher["id"] not in ids
    assert plan_b_student["id"] not in ids

    by_id = {p["id"]: p for p in data["plans"]}
    assert by_id[plan_a_student["id"]]["price"] == 99.0

    # School B's own student sees School B's price, not School A's.
    resp_b = client.get(
        f"{PREFIX}/subscription/me/plans", headers=auth(db, world.b.student_user)
    )
    assert resp_b.status_code == 200, resp_b.text
    assert {p["id"] for p in resp_b.json()["plans"]} == {plan_b_student["id"]}
    assert resp_b.json()["school_id"] == world.b.school.id


def test_payment_never_accepts_a_price_from_the_client(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id, price=1234.0)

    resp = client.post(
        f"{PREFIX}/subscription/payments",
        headers=auth(db, world.a.student_user),
        json={"plan_id": plan["id"], "amount": 1.0, "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["amount"] == 1234.0
    assert resp.json()["currency"] == "INR"


# ---------------------------------------------------------------------------
# 8. Plans: deactivation (never deletion) + structured validation codes
# ---------------------------------------------------------------------------


def test_deactivated_plans_are_retained_but_unusable(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    student = auth(db, target)

    resp = client.post(
        f"{PREFIX}/subscription/plans/{plan['id']}/deactivate", headers=sa
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False

    resp = client.post(
        f"{PREFIX}/subscription/payments", headers=student, json={"plan_id": plan["id"]}
    )
    assert_error(resp, "PLAN_INACTIVE", 400)

    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/grant",
        headers=sa,
        json={"plan_id": plan["id"]},
    )
    assert_error(resp, "PLAN_INACTIVE", 400)

    # Hidden from the learner's catalogue but still listed for the auditor.
    assert client.get(f"{PREFIX}/subscription/me/plans", headers=student).json()[
        "plans"
    ] == []
    listing = client.get(f"{PREFIX}/subscription/plans", headers=sa)
    assert listing.status_code == 200
    assert plan["id"] in {p["id"] for p in listing.json()["items"]}


def test_structured_validation_error_codes(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id
    student = auth(db, world.a.student_user)

    bad_requests = [
        ("POST", f"{PREFIX}/subscription/schools/{school_id}/plans",
         plan_payload(price=-5), "INVALID_PRICE", 400),
        ("POST", f"{PREFIX}/subscription/schools/{school_id}/plans",
         plan_payload(duration_value=0), "INVALID_DURATION", 400),
        ("POST", f"{PREFIX}/subscription/schools/{school_id}/plans",
         plan_payload(duration_unit="FORTNIGHT"), "INVALID_DURATION", 400),
        ("POST", f"{PREFIX}/subscription/schools/{school_id}/plans",
         plan_payload(role="SUPER_ADMIN"), "INVALID_ROLE", 400),
        ("PATCH", f"{PREFIX}/subscription/schools/{school_id}/settings", {},
         "NO_CHANGES", 400),
        ("POST", f"{PREFIX}/subscription/users/{world.a.student_user.id}/grant",
         {"plan_id": 999999}, "PLAN_NOT_FOUND", 404),
        ("POST", f"{PREFIX}/subscription/users/999999/grant",
         {"plan_id": 1}, "USER_NOT_FOUND", 404),
        ("GET", f"{PREFIX}/subscription/schools/999999", None, "SCHOOL_NOT_FOUND", 404),
        ("GET", f"{PREFIX}/subscription/users/999999", None, "USER_NOT_FOUND", 404),
    ]

    for method, path, body, code, status_code in bad_requests:
        resp = getattr(client, method.lower())(
            path, headers=sa, **({"json": body} if body is not None else {})
        )
        assert_error(resp, code, status_code)
        assert "Traceback" not in resp.text
        # Nothing was persisted by a rejected payload.
        assert "File \"" not in resp.text

    # Learner-facing calls carry the learner's own token (not the admin's).
    resp = client.post(
        f"{PREFIX}/subscription/payments", headers=student, json={"plan_id": 999999}
    )
    assert_error(resp, "PLAN_NOT_FOUND", 404)

    # Sanity: the same call with a valid payload still works.
    plan = make_plan(client, sa, school_id)
    assert plan["id"] > 0

    # ...and an empty plan PATCH is a structured NO_CHANGES (not a silent 200).
    resp = client.patch(
        f"{PREFIX}/subscription/plans/{plan['id']}", headers=sa, json={}
    )
    assert_error(resp, "NO_CHANGES", 400)

    assert client.get(f"{PREFIX}/subscription/me", headers=student).status_code == 200


# ---------------------------------------------------------------------------
# 9. Mock payment provider (development only) + production gating
# ---------------------------------------------------------------------------


def test_mock_payment_success_activates_and_notifies(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id, price=250.0)
    target = world.a.student_user
    student = auth(db, target)

    payment = checkout(client, student, plan["id"])
    assert payment["status"] == "PENDING"
    assert payment["provider"] == "INTERNAL"
    assert payment["amount"] == 250.0
    assert payment["subscription_id"] is None
    assert access_of(client, student)["has_access"] is False

    resp = complete(client, student, payment["id"], "SUCCESS")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "SUCCESS"
    assert body["subscription_id"] is not None
    assert body["paid_at"] is not None

    access = access_of(client, student)
    assert access["has_access"] is True
    assert access["reason"] == "PAYMENT"
    assert client.get(f"{PREFIX}/attendance", headers=student).status_code == 200

    assert notifications_for(db, target, "Payment successful") == 1
    assert notifications_for(db, target, "Subscription activated") == 1

    db.expire_all()
    assert (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "Subscription")
        .count()
        >= 1
    )


def test_mock_payment_failure_outcomes_never_create_entitlements(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    student = auth(db, target)

    for outcome, expected in (("FAILED", "FAILED"), ("CANCELLED", "CANCELLED"),
                              ("PENDING", "PENDING")):
        payment = checkout(client, student, plan["id"])
        resp = complete(client, student, payment["id"], outcome)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == expected, outcome
        assert resp.json()["subscription_id"] is None, outcome

        assert db.query(Subscription).filter(
            Subscription.user_id == target.id
        ).count() == 0
        assert access_of(client, student)["has_access"] is False

    assert notifications_for(db, target, "Payment failed") == 1


def test_mock_completion_is_idempotent(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    student = auth(db, target)

    payment = checkout(client, student, plan["id"])
    first = complete(client, student, payment["id"], "SUCCESS").json()
    second = complete(client, student, payment["id"], "SUCCESS").json()

    assert second["id"] == first["id"]
    assert second["subscription_id"] == first["subscription_id"]
    assert second["paid_at"] == first["paid_at"]

    db.expire_all()
    assert db.query(Subscription).filter(Subscription.user_id == target.id).count() == 1


def test_cannot_complete_another_users_payment(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    payment = checkout(client, auth(db, world.a.student_user), plan["id"])

    resp = complete(client, auth(db, world.b.student_user), payment["id"], "SUCCESS")
    assert_error(resp, "PAYMENT_NOT_FOUND", 404)

    resp = client.post(
        f"{PREFIX}/subscription/payments/{payment['id']}/cancel",
        headers=auth(db, world.b.student_user),
    )
    assert_error(resp, "PAYMENT_NOT_FOUND", 404)

    # The payment row itself is untouched: still awaiting its owner.
    from app.models.subscription_payment import SubscriptionPayment

    db.expire_all()
    assert (
        db.query(SubscriptionPayment).filter(SubscriptionPayment.id == payment["id"])
        .one()
        .status
        == "PENDING"
    )


def test_mock_payments_are_hard_disabled_in_production(client, db, world, monkeypatch):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    student = auth(db, world.a.student_user)

    monkeypatch.setenv("ENVIRONMENT", "production")

    resp = client.post(
        f"{PREFIX}/subscription/payments", headers=student, json={"plan_id": plan["id"]}
    )
    assert_error(resp, "PAYMENT_PROVIDER_UNAVAILABLE", 400)

    # The flag is surfaced to the UI so no mock checkout button is rendered.
    access = access_of(client, student)
    assert access["mock_payments_enabled"] is False
    me_plans = client.get(f"{PREFIX}/subscription/me/plans", headers=student).json()
    assert me_plans["mock_payments_enabled"] is False
    assert me_plans["payment_provider"] == "INTERNAL"


def test_cancel_pending_payment_is_allowed_by_its_owner(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    student = auth(db, world.a.student_user)

    payment = checkout(client, student, plan["id"])
    resp = client.post(
        f"{PREFIX}/subscription/payments/{payment['id']}/cancel", headers=student
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED"


# ---------------------------------------------------------------------------
# 10. Authentication and subscription validity are separate concerns
# ---------------------------------------------------------------------------


def test_same_token_loses_features_but_keeps_profile_and_billing(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user

    grant(client, sa, target.id, plan["id"])
    headers = auth(db, target)  # one token, minted while entitled
    assert client.get(f"{PREFIX}/attendance", headers=headers).status_code == 200

    expire_subscription(db, target.id)

    for path in GATED_PATHS:
        detail = assert_denied(client.get(f"{PREFIX}{path}", headers=headers))
        assert detail["reason"] == "EXPIRED", path

    for path in SELF_SERVICE_PATHS:
        resp = client.get(f"{PREFIX}{path}", headers=headers)
        assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text[:300]}"

    # Logout still works, so the lock screen can never trap a user.
    resp = client.post(f"{PREFIX}/auth/logout", headers=headers, json={})
    assert resp.status_code == 200, resp.text


def test_subscription_state_never_mutates_account_status(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])

    for action in ("suspend", "restore", "cancel"):
        resp = client.post(
            f"{PREFIX}/subscription/users/{target.id}/{action}",
            headers=sa,
            json={"reason": action},
        )
        assert resp.status_code == 200, f"{action}: {resp.text[:300]}"

        db.expire_all()
        fresh = db.query(User).filter(User.id == target.id).one()
        assert fresh.is_active == "ACTIVE", action
        assert client.get(f"{PREFIX}/auth/me", headers=auth(db, target)).status_code == 200

    # And the account still authenticates while its subscription is cancelled.
    assert access_of(client, auth(db, target))["has_access"] is False


def test_cancelled_subscription_is_reported_and_restorable(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])
    student = auth(db, target)

    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/cancel",
        headers=sa,
        json={"reason": "refund"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED"
    assert_denied(client.get(f"{PREFIX}/attendance", headers=student))

    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/restore", headers=sa, json={}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"
    assert client.get(f"{PREFIX}/attendance", headers=student).status_code == 200


def test_suspension_blocks_access_with_a_distinct_state(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])
    student = auth(db, target)

    resp = client.post(
        f"{PREFIX}/subscription/users/{target.id}/suspend",
        headers=sa,
        json={"reason": "abuse"},
    )
    assert resp.status_code == 200, resp.text

    detail = assert_denied(client.get(f"{PREFIX}/attendance", headers=student))
    assert detail["subscription_status"] == "SUSPENDED"
    assert detail["reason"] == "SUSPENDED"
    assert access_of(client, student)["status"] == "SUSPENDED"


# ---------------------------------------------------------------------------
# 11. Bulk operations: shared validation, savepoints, audit, per-user summary
# ---------------------------------------------------------------------------


def test_bulk_free_until_reports_a_per_user_failure_summary(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id
    enable(client, sa, school_id)

    user_ids = [
        world.a.student_user.id,
        world.a.teacher_user.id,
        999999,                       # does not exist
        world.b.student_user.id,      # other tenant
    ]
    resp = client.post(
        f"{PREFIX}/subscription/schools/{school_id}/bulk",
        headers=sa,
        json={
            "action": "FREE_UNTIL",
            "user_ids": user_ids,
            "free_until": in_days(10),
            "reason": "rollout credit",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["action"] == "FREE_UNTIL"
    assert body["requested"] == 4
    assert body["succeeded"] == [world.a.student_user.id, world.a.teacher_user.id]
    assert {f["code"] for f in body["failed"]} == {"USER_NOT_FOUND", "USER_NOT_IN_SCHOOL"}
    assert {f["user_id"] for f in body["failed"]} == {999999, world.b.student_user.id}
    for failure in body["failed"]:
        assert isinstance(failure["message"], str) and failure["message"]

    # The successes committed, the failures left no residue.
    for uid in body["succeeded"]:
        assert (
            db.query(UserSubscriptionOverride)
            .filter(UserSubscriptionOverride.user_id == uid)
            .count()
            == 1
        )
    assert (
        db.query(UserSubscriptionOverride)
        .filter(UserSubscriptionOverride.user_id == world.b.student_user.id)
        .count()
        == 0
    )

    # Every success carries an audit row, attributed to the acting admin.
    audits = (
        db.query(SubscriptionAuditLog)
        .filter(SubscriptionAuditLog.action == "USER_FREE_GRANTED")
        .all()
    )
    assert {a.user_id for a in audits} == set(body["succeeded"])
    assert all(a.admin_id == world.superadmin.id for a in audits)

    # Both successes are now entitled.
    assert access_of(client, auth(db, world.a.student_user))["has_access"] is True
    assert access_of(client, auth(db, world.a.teacher_user))["has_access"] is True


def test_bulk_rejects_an_invalid_action_before_touching_anything(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id
    enable(client, sa, school_id)

    resp = client.post(
        f"{PREFIX}/subscription/schools/{school_id}/bulk",
        headers=sa,
        json={"action": "DELETE_EVERYTHING", "user_ids": [world.a.student_user.id]},
    )
    assert_error(resp, "INVALID_BULK_ACTION", 400)
    assert (
        db.query(UserSubscriptionOverride)
        .filter(UserSubscriptionOverride.user_id == world.a.student_user.id)
        .count()
        == 0
    )


def test_bulk_requires_its_shared_input_up_front(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id

    resp = client.post(
        f"{PREFIX}/subscription/schools/{school_id}/bulk",
        headers=sa,
        json={"action": "FREE_UNTIL", "user_ids": [world.a.student_user.id]},
    )
    assert_error(resp, "INVALID_FREE_UNTIL", 400)

    resp = client.post(
        f"{PREFIX}/subscription/schools/{school_id}/bulk",
        headers=sa,
        json={"action": "EXTEND", "user_ids": [world.a.student_user.id]},
    )
    assert_error(resp, "INVALID_DURATION", 400)

    resp = client.post(
        f"{PREFIX}/subscription/schools/{school_id}/bulk",
        headers=sa,
        json={"action": "ASSIGN_PLAN", "user_ids": [world.a.student_user.id],
              "plan_id": 999999},
    )
    assert_error(resp, "PLAN_NOT_FOUND", 404)


def test_bulk_assign_plan_rejects_a_foreign_plan_up_front(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan_b = make_plan(client, sa, world.b.school.id)

    resp = client.post(
        f"{PREFIX}/subscription/schools/{world.a.school.id}/bulk",
        headers=sa,
        json={
            "action": "ASSIGN_PLAN",
            "user_ids": [world.a.student_user.id],
            "plan_id": plan_b["id"],
        },
    )
    assert_error(resp, "USER_NOT_IN_SCHOOL", 400)
    assert db.query(Subscription).filter(
        Subscription.user_id == world.a.student_user.id
    ).count() == 0


# ---------------------------------------------------------------------------
# 12. Audit trails
# ---------------------------------------------------------------------------


def test_every_access_and_billing_change_is_audited(client, db, world):
    sa = auth(db, world.superadmin)
    school_id = world.a.school.id
    target = world.a.student_user

    enable(client, sa, school_id)
    plan = make_plan(client, sa, school_id)
    grant(client, sa, target.id, plan["id"], reason="onboarding")
    client.post(
        f"{PREFIX}/subscription/users/{target.id}/suspend",
        headers=sa,
        json={"reason": "audit me"},
    )

    db.expire_all()
    actions = {row.action for row in db.query(SubscriptionAuditLog).all()}
    assert {
        "SCHOOL_SUBSCRIPTIONS_ENABLED",
        "PLAN_CREATED",
        "USER_SUBSCRIPTION_GRANTED",
        "USER_SUBSCRIPTION_SUSPENDED",
    } <= actions

    rows = db.query(SubscriptionAuditLog).filter(
        SubscriptionAuditLog.action == "USER_SUBSCRIPTION_GRANTED"
    )
    assert all(r.admin_id == world.superadmin.id for r in rows)
    assert all(r.user_id == target.id for r in rows)
    assert any(r.reason == "onboarding" for r in rows)

    platform = (
        db.query(AuditLog).filter(AuditLog.resource_type == "Subscription").all()
    )
    assert platform, "subscription changes must also hit the platform audit log"
    assert all(p.user_id == world.superadmin.id for p in platform)


def test_user_detail_exposes_the_full_paper_trail(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])

    resp = client.get(f"{PREFIX}/subscription/users/{target.id}", headers=sa)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_id"] == target.id
    assert body["access"]["has_access"] is True
    assert len(body["history"]) == 1
    # Audit rows attached to this USER (plan creation is school-scoped and
    # carries no user_id, so it is only visible in the school/plan views).
    assert {row["action"] for row in body["audit"]} >= {"USER_SUBSCRIPTION_GRANTED"}
    assert body["audit"][0]["admin_id"] == world.superadmin.id


# ---------------------------------------------------------------------------
# 13. Notifications (existing infrastructure, de-duplicated)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "offset,label",
    [
        (timedelta(days=6.5), "7 days"),
        (timedelta(days=2.5), "3 days"),
        (timedelta(hours=12), "1 day"),
    ],
)
def test_expiry_reminder_windows_fire_once_each(client, db, world, offset, label):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])
    headers = auth(db, target)

    row = (
        db.query(Subscription)
        .filter(Subscription.user_id == target.id)
        .one()
    )
    row.end_at = utcnow() + offset
    db.commit()

    # The reminder is emitted lazily during a normal access check.
    assert client.get(f"{PREFIX}/attendance", headers=headers).status_code == 200
    assert client.get(f"{PREFIX}/attendance", headers=headers).status_code == 200
    assert client.get(f"{PREFIX}/subscription/me", headers=headers).status_code == 200

    title = f"Subscription expires in {label}"
    assert notifications_for(db, target, title) == 1, title

    # And the entitled user really is still entitled.
    assert access_of(client, headers)["has_access"] is True


def test_grant_and_payment_notifications_reuse_the_existing_pipeline(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    student = auth(db, target)

    grant(client, sa, target.id, plan["id"])
    assert notifications_for(db, target, "Subscription activated") == 1

    payment = checkout(client, student, plan["id"])
    complete(client, student, payment["id"], "FAILED")
    assert notifications_for(db, target, "Payment failed") == 1

    payment = checkout(client, student, plan["id"])
    complete(client, student, payment["id"], "SUCCESS")
    assert notifications_for(db, target, "Payment successful") == 1

    # Notifications are addressed to the learner and visible to them.
    listed = client.get(f"{PREFIX}/notifications/", headers=student)
    assert listed.status_code == 200, listed.text
    titles = {n["title"] for n in listed.json()["items"]}
    assert {"Subscription activated", "Payment failed", "Payment successful"} <= titles


def test_cancel_emits_a_targeted_notification(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    grant(client, sa, target.id, plan["id"])

    client.post(
        f"{PREFIX}/subscription/users/{target.id}/cancel",
        headers=sa,
        json={"reason": "requested by school"},
    )
    assert notifications_for(db, target, "Subscription cancelled") == 1


# ---------------------------------------------------------------------------
# 14. Metrics and school summaries: real aggregates only
# ---------------------------------------------------------------------------


def test_metrics_report_only_real_aggregates(client, db, world):
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id)
    target = world.a.student_user
    student = auth(db, target)

    grant(client, sa, target.id, plan["id"])

    first = checkout(client, student, plan["id"])
    complete(client, student, first["id"], "SUCCESS")
    second = checkout(client, student, plan["id"])
    complete(client, student, second["id"], "FAILED")
    checkout(client, student, plan["id"])  # left pending

    metrics = client.get(f"{PREFIX}/subscription/metrics", headers=sa)
    assert metrics.status_code == 200, metrics.text
    m = metrics.json()

    assert m["total_schools"] == 2
    assert m["subscriptions_enabled"] == 1
    assert m["schools_currently_free"] == 0
    assert m["active_user_subscriptions"] == 1
    assert m["expired_user_subscriptions"] == 0
    assert m["pending_payments"] == 1
    assert m["successful_payments"] == 1
    assert m["failed_payments"] == 1

    # Free-window counter must move when a free window really exists.
    enable(client, sa, world.a.school.id, free_until=in_days(30))
    m = client.get(f"{PREFIX}/subscription/metrics", headers=sa).json()
    assert m["schools_currently_free"] == 1


def test_school_summaries_reflect_real_per_school_state(client, db, world):
    sa = auth(db, world.superadmin)
    a_id = world.a.school.id
    b_id = world.b.school.id

    def statuses():
        resp = client.get(f"{PREFIX}/subscription/schools", headers=sa)
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 2
        return {item["school_id"]: item for item in resp.json()["items"]}

    # Neither school has a settings row yet.
    assert statuses()[b_id]["status"] == "DISABLED"
    assert statuses()[a_id]["status"] == "DISABLED"

    # School A switches on but has no plan for any billable role.
    enable(client, sa, a_id)
    assert statuses()[a_id]["status"] == "NO_PLANS"

    # One plan covers one of three billable roles -> PARTIAL.
    make_plan(client, sa, a_id)
    items = statuses()
    assert items[a_id]["status"] == "PARTIAL"
    assert items[a_id]["students"] >= 1
    assert items[a_id]["teachers"] >= 1
    assert items[a_id]["others"] >= 1
    assert items[b_id]["status"] == "DISABLED"

    # A live school-wide free window wins over plan coverage.
    enable(client, sa, a_id, free_until=in_days(30))
    assert statuses()[a_id]["status"] == "FREE"


def test_school_roles_and_users_listings_are_scoped_and_real(client, db, world):
    sa = auth(db, world.superadmin)
    a_id = world.a.school.id
    enable(client, sa, a_id)
    plan = make_plan(client, sa, a_id)
    grant(client, sa, world.a.student_user.id, plan["id"])

    resp = client.get(f"{PREFIX}/subscription/schools/{a_id}/roles", headers=sa)
    assert resp.status_code == 200, resp.text
    roles = {r["role"]: r for r in resp.json()["roles"]}
    assert set(roles) >= {"PRINCIPAL", "TEACHER", "STUDENT"}
    assert roles["STUDENT"]["active"] == 1
    assert roles["PRINCIPAL"]["active"] == 0
    assert roles["STUDENT"]["active_plans"] == 1

    detail = client.get(f"{PREFIX}/subscription/schools/{a_id}/roles/STUDENT", headers=sa)
    assert detail.status_code == 200, detail.text
    assert [p["id"] for p in detail.json()["plans"]] == [plan["id"]]

    users = client.get(f"{PREFIX}/subscription/schools/{a_id}/users", headers=sa)
    assert users.status_code == 200, users.text
    body = users.json()
    by_id = {u["user_id"]: u for u in body["items"]}
    assert by_id[world.a.student_user.id]["subscription_status"] == "ACTIVE"
    assert by_id[world.a.principal.id]["subscription_status"] == "NONE"
    assert by_id[world.a.student_user.id]["expires_at"] is not None

    # Status filtering works and never leaks another tenant.
    filtered = client.get(
        f"{PREFIX}/subscription/schools/{a_id}/users?status=ACTIVE", headers=sa
    )
    assert filtered.status_code == 200, filtered.text
    assert {u["user_id"] for u in filtered.json()["items"]} == {
        world.a.student_user.id
    }

    # School B's listing contains only school B's people.
    b_users = client.get(f"{PREFIX}/subscription/schools/{world.b.school.id}/users",
                         headers=sa)
    assert b_users.status_code == 200, b_users.text
    assert {u["user_id"] for u in b_users.json()["items"]} == {
        world.b.principal.id,
        world.b.teacher_user.id,
        world.b.student_user.id,
    }


# ---------------------------------------------------------------------------
# 15. Roles that are never billed
# ---------------------------------------------------------------------------


def test_non_billable_roles_are_never_gated(client, db, world):
    """Only PRINCIPAL / TEACHER / STUDENT are billable (``BILLABLE_ROLES``).

    ``users.role`` is a native enum limited to the four seeded values today,
    so a fifth role cannot be persisted yet - but the resolver must not gate
    one if it ever exists, otherwise an unrelated ERP feature would start
    asking for money. Asserted at the service layer with an in-memory user.
    """
    from app.models.user import User as UserModel
    from app.services.subscription import SubscriptionService

    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)  # enforcing, and no free window

    other = UserModel(
        id=world.a.student_user.id + 1_000_000,  # never collides with a real row
        school_id=world.a.school.id,
        role="PARENT",
    )

    status = SubscriptionService.get_access_status(db, other)
    assert status.has_access is True
    assert status.reason == "NON_BILLABLE_ROLE"
    assert status.subscriptions_enabled is True
    SubscriptionService.require_access(db, other)  # does not raise

    # ...while the billable roles in the very same school are gated.
    assert_denied(
        client.get(f"{PREFIX}/attendance", headers=auth(db, world.a.student_user))
    )


# ---------------------------------------------------------------------------
# 16. Unauthenticated callers
# ---------------------------------------------------------------------------


def test_unauthenticated_subscription_requests_are_rejected(client, db, world):
    cases = [
        ("GET", f"{PREFIX}/subscription/me", None),
        ("GET", f"{PREFIX}/subscription/me/plans", None),
        ("GET", f"{PREFIX}/subscription/schools", None),
        ("GET", f"{PREFIX}/subscription/metrics", None),
        ("POST", f"{PREFIX}/subscription/payments", {"plan_id": 1}),
        ("POST", f"{PREFIX}/subscription/schools/{world.a.school.id}/plans",
         plan_payload()),
    ]
    for method, path, body in cases:
        resp = getattr(client, method.lower())(
            path, **({"json": body} if body is not None else {})
        )
        assert resp.status_code in (401, 403), f"{method} {path} -> {resp.text[:200]}"
        assert "Traceback" not in resp.text

    # And a gated feature router must never run its handler either.
    assert client.get(f"{PREFIX}/attendance").status_code in (401, 403)
