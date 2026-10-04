"""Razorpay (RAZORPAY provider): UPI-only, server-side verification, webhooks.

Everything is asserted through the REAL HTTP surface (or the real service
entry points) against real rows. The Razorpay SDK is the only thing faked:
``build_client`` is monkeypatched, so the suite NEVER opens a network
connection - no key, no sandbox, no internet.

Covered guarantees
-----------------
* the order amount comes from the DATABASE plan (paise, no float maths) and
  the checkout response carries only PUBLIC values (key id, order id, paise)
* a valid signature + a fetched CAPTURED UPI payment activates the plan
* a bad signature, an amount mismatch, a currency mismatch and a non-UPI
  (card) payment are all rejected without touching any entitlement
* ``authorized`` (not yet captured) stays PENDING until the webhook
* the webhook signature is checked over the RAW bytes BEFORE any DB write;
  a bad signature is 400, unknown events/orders are ACKed with 200
* callback + webhook + replay never double-extend a subscription
* FAILED marks the row FAILED and notifies the owner
* another user's payment id is a 404 (no existence leak)
* the INTERNAL mock provider still works in development and is hard
  disabled in production
* missing Razorpay credentials are a structured 400 (and a startup error
  in production), never a stack trace and never a leaked value
"""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any, Dict, Optional

import pytest
from razorpay.errors import SignatureVerificationError

from app.core.config import settings as app_settings
from app.models.subscription import Subscription
from app.models.subscription_payment import SubscriptionPayment
from app.services.payment_providers import razorpay as razorpay_module
from tests.helpers import auth
from tests.test_subscription import (
    PREFIX,
    access_of,
    assert_error,
    checkout,
    enable,
    make_plan,
    notifications_for,
)

# Test-mode credentials. Public id in the response is expected; the SECRETS
# must never appear in any response body (asserted below).
KEY_ID = "rzp_test_1234567890abcdef"
KEY_SECRET = "test_key_secret_never_log_me"
WEBHOOK_SECRET = "test_webhook_secret_never_log_me"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def payment_signature(order_id: str, payment_id: str, secret: str = KEY_SECRET) -> str:
    """``HMAC_SHA256(f"{order_id}|{payment_id}", key_secret)`` - Razorpay's rule."""
    return hmac_hex(secret, f"{order_id}|{payment_id}".encode("utf-8"))


class FakeUtility:
    """Mirrors ``razorpay.Client.utility``: raises on mismatch, like the SDK."""

    def __init__(self, key_secret: str, webhook_secret: str):
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret

    def verify_payment_signature(self, payload: Dict[str, Any]) -> bool:
        expected = payment_signature(
            str(payload["razorpay_order_id"]),
            str(payload["razorpay_payment_id"]),
            self._key_secret,
        )
        if not hmac.compare_digest(expected, str(payload["razorpay_signature"])):
            raise SignatureVerificationError("payment signature mismatch")
        return True

    def verify_webhook_signature(self, body: str, signature: str, secret: str) -> bool:
        expected = hmac_hex(secret, body.encode("utf-8"))
        if not hmac.compare_digest(expected, str(signature)):
            raise SignatureVerificationError("webhook signature mismatch")
        return True


class FakeOrders:
    def __init__(self, client: "FakeClient"):
        self._client = client

    def create(self, data: Dict[str, Any], timeout: Any = None) -> Dict[str, Any]:
        self._client.calls.append(("order.create", dict(data), timeout))
        order_id = f"order_test{self._client.order_seq:04d}"
        self._client.order_seq += 1
        self._client.last_order = dict(data, id=order_id)
        return {
            "id": order_id,
            "entity": "order",
            "amount": data["amount"],
            "currency": data["currency"],
            "status": "created",
        }

    def payments(self, order_id: str, timeout: Any = None) -> list:
        self._client.calls.append(("order.payments", order_id, timeout))
        return [dict(self._client.payment_entity)]


class FakePaymentResource:
    def __init__(self, client: "FakeClient"):
        self._client = client

    def fetch(self, payment_id: str, timeout: Any = None) -> Dict[str, Any]:
        self._client.calls.append(("payment.fetch", payment_id, timeout))
        if self._client.fetch_error is not None:
            raise self._client.fetch_error
        entity = dict(self._client.payment_entity)
        entity.setdefault("id", payment_id)
        return entity


class FakeRefunds:
    def __init__(self, client: "FakeClient"):
        self._client = client

    def create(self, data: Dict[str, Any], timeout: Any = None) -> Dict[str, Any]:
        self._client.calls.append(("refund.create", dict(data), timeout))
        return {"id": "rfnd_test0001", "status": "processed"}


class FakeClient:
    """Stand-in for ``razorpay.Client`` wired with an in-memory payment."""

    def __init__(self, key_secret: str = KEY_SECRET, webhook_secret: str = WEBHOOK_SECRET):
        self.utility = FakeUtility(key_secret, webhook_secret)
        self.order = FakeOrders(self)
        self.payment = FakePaymentResource(self)
        self.refund = FakeRefunds(self)
        self.calls = []
        self.retry_enabled: Optional[bool] = None
        self.order_seq = 1
        self.last_order: Optional[Dict[str, Any]] = None
        self.fetch_error: Optional[Exception] = None
        self.payment_entity: Dict[str, Any] = {
            "id": "pay_test0001",
            "order_id": "",
            "amount": 0,
            "currency": "INR",
            "method": "upi",
            "status": "captured",
        }

    def enable_retry(self, enabled: bool) -> None:
        self.retry_enabled = enabled


@pytest.fixture
def razorpay(monkeypatch):
    """Configure the app for RAZORPAY and seam the SDK constructor.

    ``build_client`` itself stays REAL (it must keep disabling retries); only
    ``razorpay.Client`` is replaced, so the suite never touches the network.
    """
    fake = FakeClient()
    monkeypatch.setattr(app_settings, "PAYMENT_PROVIDER", "RAZORPAY")
    monkeypatch.setattr(app_settings, "RAZORPAY_KEY_ID", KEY_ID)
    monkeypatch.setattr(app_settings, "RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setattr(app_settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr(
        razorpay_module.razorpay, "Client", lambda auth=None: fake
    )
    return fake


def prepare(client, db, world, **plan_overrides):
    """Enabled school + billable plan + the owning student's headers."""
    sa = auth(db, world.superadmin)
    enable(client, sa, world.a.school.id)
    plan = make_plan(client, sa, world.a.school.id, **plan_overrides)
    student = auth(db, world.a.student_user)
    return plan, student


def stub_payment(fake: FakeClient, order_id: str, **overrides: Any) -> str:
    """Configure what ``payment.fetch`` will answer for this order."""
    entity = {
        "id": "pay_test0001",
        "order_id": order_id,
        "amount": 0,
        "currency": "INR",
        "method": "upi",
        "status": "captured",
    }
    entity.update(overrides)
    fake.payment_entity = entity
    return str(entity["id"])


def verify(client, headers, payment_id, order_id, provider_payment_id, signature=None):
    """POST /payments/{id}/verify exactly as Checkout.js's handler does."""
    payload = {
        "razorpay_payment_id": provider_payment_id,
        "razorpay_signature": signature
        if signature is not None
        else payment_signature(order_id, provider_payment_id),
    }
    return client.post(
        f"{PREFIX}/subscription/payments/{payment_id}/verify",
        headers=headers,
        json=payload,
    )


def webhook_body(
    order_id: str,
    *,
    event: str = "payment.captured",
    payment_id: str = "pay_test0001",
    paise: int = 0,
    currency: str = "INR",
    method: str = "upi",
    status: str = "captured",
) -> bytes:
    return json.dumps(
        {
            "event": event,
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": paise,
                        "currency": currency,
                        "method": method,
                        "status": status,
                    }
                }
            },
        }
    ).encode("utf-8")


def post_webhook(client, body: bytes, *, signature: Optional[str] = None, secret: str = WEBHOOK_SECRET):
    sig = hmac_hex(secret, body) if signature is None else signature
    return client.post(
        f"{PREFIX}/subscriptions/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )


def row(db, payment_id: int) -> SubscriptionPayment:
    db.expire_all()
    return (
        db.query(SubscriptionPayment)
        .filter(SubscriptionPayment.id == payment_id)
        .one()
    )


def subscriptions_of(db, user_id: int):
    return db.query(Subscription).filter(Subscription.user_id == user_id).all()


# ---------------------------------------------------------------------------
# 1. Checkout: amount from the DB, paise, public values only
# ---------------------------------------------------------------------------


def test_checkout_amount_comes_from_the_plan_in_paise(client, db, world, razorpay):
    plan, student = prepare(client, db, world, price=199.5)

    resp = client.post(
        f"{PREFIX}/subscription/payments",
        headers=student,
        # A client-sent price must be ignored: only plan_id is accepted.
        json={"plan_id": plan["id"], "price": 1.0, "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["provider"] == "RAZORPAY"
    assert body["amount"] == 199.5
    assert body["currency"] == "INR"
    assert body["status"] == "PENDING"
    assert body["amount_paise"] == 19950
    assert body["razorpay_key_id"] == KEY_ID
    assert body["razorpay_order_id"] == body["provider_order_id"]
    assert body["razorpay_order_id"].startswith("order_test")

    # Secrets never leave the server.
    assert KEY_SECRET not in resp.text
    assert WEBHOOK_SECRET not in resp.text

    # The SDK was called exactly once, without retries, with an explicit
    # timeout and with OUR amount - in paise.
    creates = [call for call in razorpay.calls if call[0] == "order.create"]
    assert len(creates) == 1
    assert creates[0][1]["amount"] == 19950
    assert creates[0][1]["currency"] == "INR"
    assert creates[0][2] is not None  # timeout passed
    assert razorpay.retry_enabled is False

    me_plans = client.get(f"{PREFIX}/subscription/me/plans", headers=student).json()
    assert me_plans["payment_provider"] == "RAZORPAY"


# ---------------------------------------------------------------------------
# 2. Browser callback: verified UPI capture activates the plan
# ---------------------------------------------------------------------------


def test_valid_signature_and_captured_upi_activates_the_plan(client, db, world, razorpay):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    payment_id_ref = stub_payment(
        razorpay, payment["provider_order_id"], amount=25000
    )

    resp = verify(client, student, payment["id"], payment["provider_order_id"], payment_id_ref)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "SUCCESS"
    assert body["provider_payment_id"] == payment_id_ref
    assert body["subscription_id"] is not None
    assert body["paid_at"] is not None

    assert access_of(client, student)["has_access"] is True
    assert access_of(client, student)["reason"] == "PAYMENT"
    assert len(subscriptions_of(db, target.id)) == 1
    assert notifications_for(db, target, "Payment successful") == 1
    assert notifications_for(db, target, "Subscription activated") == 1

    # The client is never trusted for facts: the server fetched the payment.
    assert any(call[0] == "payment.fetch" for call in razorpay.calls)


def test_order_id_used_for_verification_comes_from_the_database(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world)
    payment = checkout(client, student, plan["id"])
    payment_id_ref = stub_payment(razorpay, payment["provider_order_id"], amount=10000)

    resp = client.post(
        f"{PREFIX}/subscription/payments/{payment['id']}/verify",
        headers=student,
        json={
            # Extra fields are ignored: the server reads OUR row, so a client
            # cannot point the verification at another order.
            "razorpay_order_id": "order_something_else",
            "razorpay_payment_id": payment_id_ref,
            "razorpay_signature": payment_signature(
                payment["provider_order_id"], payment_id_ref
            ),
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SUCCESS"


def test_bad_signature_is_rejected_and_changes_nothing(client, db, world, razorpay):
    plan, student = prepare(client, db, world)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    stub_payment(razorpay, payment["provider_order_id"], amount=10000)

    resp = verify(
        client,
        student,
        payment["id"],
        payment["provider_order_id"],
        "pay_test0001",
        signature="f" * 64,
    )
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)

    assert row(db, payment["id"]).status == "PENDING"
    assert subscriptions_of(db, target.id) == []
    assert access_of(client, student)["has_access"] is False


def test_amount_mismatch_from_the_provider_is_rejected(client, db, world, razorpay):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    # Razorpay reports 100.00 while our plan row says 250.00.
    payment_id_ref = stub_payment(razorpay, payment["provider_order_id"], amount=10000)

    resp = verify(client, student, payment["id"], payment["provider_order_id"], payment_id_ref)
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)

    assert row(db, payment["id"]).status == "PENDING"
    assert subscriptions_of(db, target.id) == []


def test_currency_mismatch_from_the_provider_is_rejected(client, db, world, razorpay):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    payment_id_ref = stub_payment(
        razorpay, payment["provider_order_id"], amount=25000, currency="USD"
    )

    resp = verify(client, student, payment["id"], payment["provider_order_id"], payment_id_ref)
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)
    assert row(db, payment["id"]).status == "PENDING"
    assert subscriptions_of(db, target.id) == []


def test_non_upi_card_payment_is_rejected(client, db, world, razorpay):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    payment_id_ref = stub_payment(
        razorpay, payment["provider_order_id"], amount=25000, method="card"
    )

    resp = verify(client, student, payment["id"], payment["provider_order_id"], payment_id_ref)
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)
    assert row(db, payment["id"]).status == "PENDING"
    assert subscriptions_of(db, target.id) == []


def test_authorized_upi_stays_pending_until_the_webhook_captures_it(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    payment_id_ref = stub_payment(
        razorpay, payment["provider_order_id"], amount=25000, status="authorized"
    )

    resp = verify(client, student, payment["id"], payment["provider_order_id"], payment_id_ref)
    assert resp.status_code == 200, resp.text
    # Verified, but not captured yet: PENDING, no entitlement.
    assert resp.json()["status"] == "PENDING"
    assert resp.json()["subscription_id"] is None
    assert subscriptions_of(db, target.id) == []
    assert access_of(client, student)["has_access"] is False

    # Razorpay captures it a moment later - the webhook finalizes it.
    body = webhook_body(payment["provider_order_id"], paise=25000, status="captured")
    assert post_webhook(client, body).status_code == 200

    db.expire_all()
    assert row(db, payment["id"]).status == "SUCCESS"
    assert len(subscriptions_of(db, target.id)) == 1
    assert access_of(client, student)["has_access"] is True


# ---------------------------------------------------------------------------
# 3. Webhook: raw-body signature, idempotency, failure path
# ---------------------------------------------------------------------------


def test_webhook_with_a_valid_signature_finalizes_without_any_login(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])

    body = webhook_body(payment["provider_order_id"], paise=25000)
    # No Authorization header at all: authenticity is the signature only.
    resp = post_webhook(client, body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"
    assert resp.json()["payment_id"] == payment["id"]

    db.expire_all()
    saved = row(db, payment["id"])
    assert saved.status == "SUCCESS"
    assert saved.provider_payment_id == "pay_test0001"
    assert len(subscriptions_of(db, target.id)) == 1
    assert notifications_for(db, target, "Payment successful") == 1


def test_webhook_with_a_bad_signature_is_rejected_before_any_db_write(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])

    body = webhook_body(payment["provider_order_id"], paise=25000)
    resp = post_webhook(client, body, signature="0" * 64)
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)

    assert row(db, payment["id"]).status == "PENDING"
    assert subscriptions_of(db, target.id) == []

    # A missing signature header is refused too.
    resp = client.post(
        f"{PREFIX}/subscriptions/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)
    assert row(db, payment["id"]).status == "PENDING"


def test_webhook_amount_mismatch_is_acked_but_changes_nothing(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])

    # Signed by Razorpay, but the amount does not match OUR plan row.
    body = webhook_body(payment["provider_order_id"], paise=10000)
    assert post_webhook(client, body).status_code == 200

    assert row(db, payment["id"]).status == "PENDING"
    assert subscriptions_of(db, target.id) == []


def test_verify_and_webhook_race_never_double_extend(client, db, world, razorpay):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])
    payment_id_ref = stub_payment(
        razorpay, payment["provider_order_id"], amount=25000
    )

    first = verify(
        client, student, payment["id"], payment["provider_order_id"], payment_id_ref
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "SUCCESS"
    subscription_id = first.json()["subscription_id"]

    db.expire_all()
    end_before = (
        db.query(Subscription).filter(Subscription.id == subscription_id).one().end_at
    )

    # Webhook arrives late (Razorpay's normal order of events is the reverse).
    body = webhook_body(payment["provider_order_id"], paise=25000)
    assert post_webhook(client, body).status_code == 200
    # ...and Razorpay retries it.
    assert post_webhook(client, body).status_code == 200
    # ...and the browser re-verifies.
    replay = verify(
        client, student, payment["id"], payment["provider_order_id"], payment_id_ref
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["subscription_id"] == subscription_id

    db.expire_all()
    subs = subscriptions_of(db, target.id)
    assert len(subs) == 1, "a replay must never extend access twice"
    assert subs[0].end_at == end_before
    assert notifications_for(db, target, "Payment successful") == 1


def test_failed_webhook_marks_the_payment_failed_and_notifies(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    target = world.a.student_user
    payment = checkout(client, student, plan["id"])

    body = webhook_body(
        payment["provider_order_id"], event="payment.failed", paise=25000, status="failed"
    )
    assert post_webhook(client, body).status_code == 200

    db.expire_all()
    assert row(db, payment["id"]).status == "FAILED"
    assert subscriptions_of(db, target.id) == []
    assert access_of(client, student)["has_access"] is False
    assert notifications_for(db, target, "Payment failed") == 1


def test_webhook_rejects_a_non_upi_payment_even_when_signed(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    payment = checkout(client, student, plan["id"])

    body = webhook_body(payment["provider_order_id"], paise=25000, method="card")
    resp = post_webhook(client, body)
    assert_error(resp, "PAYMENT_VERIFICATION_FAILED", 400)
    assert row(db, payment["id"]).status == "PENDING"


def test_unknown_order_and_unknown_event_are_acked_without_state_changes(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world, price=250.0)
    payment = checkout(client, student, plan["id"])

    unknown_order = webhook_body("order_never_created", paise=25000)
    resp = post_webhook(client, unknown_order)
    assert resp.status_code == 200, resp.text
    assert resp.json()["payment_id"] is None

    # An event we deliberately do not act on is ACKed (so Razorpay stops
    # retrying) and leaves the payment untouched.
    ignored = webhook_body(payment["provider_order_id"], event="refund.processed", paise=25000)
    resp = post_webhook(client, ignored)
    assert resp.status_code == 200, resp.text
    assert resp.json()["payment_id"] is None
    assert row(db, payment["id"]).status == "PENDING"


# ---------------------------------------------------------------------------
# 4. Tenancy + configuration
# ---------------------------------------------------------------------------


def test_another_users_payment_is_a_404_on_read_and_verify(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world)
    payment = checkout(client, student, plan["id"])
    stub_payment(razorpay, payment["provider_order_id"], amount=10000)
    intruder = auth(db, world.b.student_user)

    resp = client.get(f"{PREFIX}/subscription/payments/{payment['id']}", headers=intruder)
    assert_error(resp, "PAYMENT_NOT_FOUND", 404)

    resp = verify(
        client,
        intruder,
        payment["id"],
        payment["provider_order_id"],
        "pay_test0001",
    )
    assert_error(resp, "PAYMENT_NOT_FOUND", 404)

    resp = client.post(
        f"{PREFIX}/subscription/payments/{payment['id']}/cancel", headers=intruder
    )
    assert_error(resp, "PAYMENT_NOT_FOUND", 404)

    assert row(db, payment["id"]).status == "PENDING"


def test_razorpay_without_credentials_is_a_structured_400(client, db, world, monkeypatch):
    plan, student = prepare(client, db, world)
    monkeypatch.setattr(app_settings, "PAYMENT_PROVIDER", "RAZORPAY")
    monkeypatch.setattr(app_settings, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(app_settings, "RAZORPAY_KEY_SECRET", None)
    monkeypatch.setattr(app_settings, "RAZORPAY_WEBHOOK_SECRET", "")

    resp = client.post(
        f"{PREFIX}/subscription/payments", headers=student, json={"plan_id": plan["id"]}
    )
    assert_error(resp, "RAZORPAY_NOT_CONFIGURED", 400)
    # Names only - never a value.
    assert "KEY_SECRET" in resp.json()["detail"]["message"]
    assert KEY_SECRET not in resp.text


def test_non_inr_plans_are_refused_by_the_provider(client, db, world, razorpay):
    from app.services.payment_providers.base import OrderRequest, PaymentProviderError
    from app.services.payment_providers.razorpay import RazorpayProvider

    provider = RazorpayProvider(
        key_id=KEY_ID, key_secret=KEY_SECRET, webhook_secret=WEBHOOK_SECRET
    )
    with pytest.raises(PaymentProviderError) as exc:
        provider.create_order(
            OrderRequest(
                user_id=1,
                school_id=1,
                plan_id=1,
                amount=Decimal("100"),
                currency="USD",
            )
        )
    assert exc.value.code == "UNSUPPORTED_CURRENCY"
    assert not any(call[0] == "order.create" for call in razorpay.calls)


def test_razorpay_pending_payment_can_be_cancelled_locally(
    client, db, world, razorpay
):
    plan, student = prepare(client, db, world)
    payment = checkout(client, student, plan["id"])

    resp = client.post(
        f"{PREFIX}/subscription/payments/{payment['id']}/cancel", headers=student
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED"
    # Razorpay orders are cancelled locally only: no provider call was made.
    assert not any(call[0] == "payment.fetch" for call in razorpay.calls)


def test_internal_mock_provider_is_unchanged_in_development(client, db, world):
    plan, student = prepare(client, db, world, price=250.0)

    payment = checkout(client, student, plan["id"])
    assert payment["provider"] == "INTERNAL"
    assert payment["razorpay_key_id"] is None
    assert payment["razorpay_order_id"] is None
    assert payment["amount_paise"] == 25000

    resp = client.post(
        f"{PREFIX}/subscription/payments/{payment['id']}/mock/complete",
        headers=student,
        json={"outcome": "SUCCESS"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SUCCESS"
    assert access_of(client, student)["has_access"] is True

    me_plans = client.get(f"{PREFIX}/subscription/me/plans", headers=student).json()
    assert me_plans["payment_provider"] == "INTERNAL"
    assert me_plans["mock_payments_enabled"] is True


def test_production_requires_all_three_razorpay_settings(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "RAZORPAY_KEY_ID", "rzp_test_public")
    monkeypatch.setattr(config.settings, "RAZORPAY_KEY_SECRET", None)
    monkeypatch.setattr(config.settings, "RAZORPAY_WEBHOOK_SECRET", "")

    with pytest.raises(RuntimeError) as exc:
        config.validate_payment_settings(environment="production", provider="RAZORPAY")

    message = str(exc.value)
    assert "RAZORPAY_KEY_SECRET" in message
    assert "RAZORPAY_WEBHOOK_SECRET" in message
    # Only names - never a value.
    assert "rzp_test_public" not in message

    # Fine outside production, and fine for the mock provider.
    config.validate_payment_settings(environment="staging", provider="RAZORPAY")
    config.validate_payment_settings(environment="production", provider="INTERNAL")
