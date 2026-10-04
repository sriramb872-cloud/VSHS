"""Password recovery regression tests (Flow A OTP + Flow B admin assisted).

Covers the security contract of the feature:

* the forgot-password response is byte-identical for unknown / no-email /
  email accounts (no account-enumeration oracle);
* only hashes of the OTP and of the reset token are ever persisted, and the
  OTP never appears in a response;
* 5 wrong OTP attempts, expiry, and single-use reset tokens;
* password policy (length / case / digit, shipped defaults, current password);
* per-login-ID rate limit (the per-IP limit is slowapi's, disabled in tests);
* role hierarchy for admin resets: Principal = own school's teachers/students,
  Super Admin = everyone, Teacher = nobody;
* forced password change + session revocation + audit trail.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.rate_limit import client_ip_key
from app.models.audit_log import AuditLog
from app.models.password_reset import PasswordResetOtp, PasswordResetRequest
from app.models.refresh_token import RefreshToken
from tests.factories import (  # noqa: F401  (``db``/``client`` come from conftest)
    DEFAULT_PASSWORD,
    make_school,
    make_user,
)
from app.services import password_reset as password_reset_service

PREFIX = "/api/v1"
CODE = "123456"
ADMIN_HELP = "Please contact your Principal or class teacher to reset your password."


def login(client, identifier: str, password: str = DEFAULT_PASSWORD):
    resp = client.post(f"{PREFIX}/auth/login", json={"mobile": identifier, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def mail_ok(monkeypatch) -> list:
    """Pretend SMTP accepted the mail; capture ``(to, subject, body)``."""
    sent = []

    def _fake_send_mail(*, to, subject, body, html=None):
        sent.append((to, subject, body))
        return True

    monkeypatch.setattr(password_reset_service, "generate_otp", lambda: CODE)
    monkeypatch.setattr(password_reset_service, "send_mail", _fake_send_mail)
    return sent


def forgot(client, login_id: str):
    return client.post(f"{PREFIX}/auth/forgot-password", json={"login_id": login_id})


def no_rate_cap(monkeypatch) -> None:
    """Lift the per-login-ID cap for tests that need many codes in a row.

    The cap itself is asserted in ``test_forgot_password_is_capped_per_login_id``.
    """
    monkeypatch.setattr(password_reset_service.settings, "FORGOT_PASSWORD_PER_HOUR", 1000)


def verify(client, login_id: str, otp: str = CODE):
    return client.post(f"{PREFIX}/auth/verify-reset-otp", json={"login_id": login_id, "otp": otp})


def complete(client, token: str, password: str = "FreshPass456!"):
    return client.post(
        f"{PREFIX}/auth/reset-password",
        json={"reset_token": token, "new_password": password},
    )


# ---------------------------------------------------------------------------
# Step 1 - forgot password
# ---------------------------------------------------------------------------


def test_forgot_password_is_identical_for_known_unknown_and_no_email(client, db):
    school = make_school(db)
    with_email = make_user(db, school, role="TEACHER")
    no_email = make_user(db, school, role="STUDENT", email=None)

    known = forgot(client, with_email.mobile)
    unknown = forgot(client, "9999999999")
    unregistered_email = forgot(client, "nobody@example.com")
    without_email = forgot(client, no_email.mobile)

    for response in (unknown, unregistered_email, without_email):
        assert response.status_code == known.status_code == 200
        assert response.json() == known.json()
    assert known.json()["message"] == (
        "If an account exists, a code has been sent."
    )


def test_forgot_password_stores_only_a_hash_and_never_returns_the_code(client, db, monkeypatch):
    sent = mail_ok(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    resp = forgot(client, user.mobile)
    assert resp.status_code == 200
    assert CODE not in resp.text  # never in the response

    row = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).one()
    assert CODE not in row.otp_hash  # never in clear text in the database
    assert row.attempts == 0 and row.used_at is None
    assert row.expires_at > datetime.utcnow()
    assert row.request_ip  # forensics

    # The code reaches the user only through the mail body.
    assert len(sent) == 1
    assert CODE in sent[0][2]
    assert user.email == sent[0][0]

    # A resend supersedes the previous code instead of stacking usable ones.
    assert forgot(client, user.mobile).status_code == 200
    rows = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).all()
    assert len(rows) == 2
    assert sum(1 for r in rows if r.used_at is None) == 1


def test_forgot_password_is_capped_per_login_id(client, db, monkeypatch):
    mail_ok(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    for _ in range(6):
        assert forgot(client, user.mobile).status_code == 200

    rows = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).all()
    assert len(rows) == password_reset_service.settings.FORGOT_PASSWORD_PER_HOUR == 5


def test_forgot_password_does_nothing_for_unknown_login_ids(client, db):
    forgot(client, "0000000000")
    assert db.query(PasswordResetOtp).count() == 0
    assert db.query(PasswordResetRequest).count() == 0


def test_failing_mail_falls_back_to_an_admin_request(client, db):
    """SMTP down (or no SMTP configured) must never strand an account."""
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    resp = forgot(client, user.mobile)
    assert resp.status_code == 200
    assert resp.json()["message"] == "If an account exists, a code has been sent."

    # The undeliverable code is retired and the account is queued for staff.
    row = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).one()
    assert row.used_at is not None
    request = db.query(PasswordResetRequest).filter(PasswordResetRequest.user_id == user.id).one()
    assert request.status == "pending"


def test_client_ip_key_prefers_the_last_forwarded_hop():
    class _FakeHeaders(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

    class _FakeRequest:
        def __init__(self, headers, host="10.0.0.9"):
            self.headers = _FakeHeaders(headers)
            self.client = type("C", (), {"host": host})()

    # No proxy -> socket peer.
    assert client_ip_key(_FakeRequest({})) == "10.0.0.9"
    # Behind a proxy: the right-most entry is the one the trusted proxy
    # appended, so a spoofed left-most value cannot bypass the limit.
    assert client_ip_key(_FakeRequest({"X-Forwarded-For": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"
    assert client_ip_key(_FakeRequest({"X-Forwarded-For": "203.0.113.9"})) == "203.0.113.9"


# ---------------------------------------------------------------------------
# Step 2 - verify the code
# ---------------------------------------------------------------------------


def test_wrong_code_five_times_invalidates_the_otp(client, db, monkeypatch):
    mail_ok(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    forgot(client, user.mobile)

    for attempt in range(5):
        wrong = verify(client, user.mobile, otp="000000" if CODE != "000000" else "111111")
        assert wrong.status_code == 400, wrong.text
        assert wrong.json()["detail"]["code"] in ("INVALID_OTP", "OTP_LOCKED")
        if attempt < 4:
            assert wrong.json()["detail"]["code"] == "INVALID_OTP"
        else:
            assert wrong.json()["detail"]["code"] == "OTP_LOCKED"

    # Even the correct code is dead now, and it cannot be retried.
    after = verify(client, user.mobile, otp=CODE)
    assert after.status_code == 400
    assert after.json()["detail"]["code"] in ("OTP_LOCKED", "INVALID_OTP")
    row = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).one()
    assert row.used_at is not None


def test_expired_code_is_rejected(client, db, monkeypatch):
    mail_ok(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    forgot(client, user.mobile)

    row = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.add(row)
    db.commit()

    resp = verify(client, user.mobile)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "OTP_EXPIRED"


def test_correct_code_yields_a_short_lived_single_use_token(client, db, monkeypatch):
    mail_ok(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    forgot(client, user.mobile)

    resp = verify(client, user.mobile)
    assert resp.status_code == 200, resp.text
    token = resp.json()["reset_token"]
    assert token and resp.json()["expires_in_minutes"] == 10

    # Only the SHA-256 hash of the token is stored - never the token itself.
    row = db.query(PasswordResetOtp).filter(PasswordResetOtp.user_id == user.id).one()
    assert token not in str(row.reset_token_hash)
    assert row.reset_token_expires_at is not None

    # The code is consumed: it cannot be verified twice.
    assert verify(client, user.mobile).status_code == 400

    # An expired token is refused.
    row.reset_token_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.add(row)
    db.commit()
    assert complete(client, token).status_code == 400


def test_unknown_login_id_at_verify_looks_like_a_wrong_code(client, db, monkeypatch):
    mail_ok(monkeypatch)
    resp = verify(client, "9999999999", otp=CODE)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_OTP"
    # Same message as a wrong code for a real account - no enumeration here.
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    forgot_ok = forgot(client, user.mobile)
    assert forgot_ok.status_code == 200
    wrong = verify(client, user.mobile, otp="999999" if CODE != "999999" else "111111")
    assert wrong.json()["detail"] == resp.json()["detail"]


def test_account_without_email_is_directed_to_staff(client, db):
    school = make_school(db)
    student = make_user(db, school, role="STUDENT", email=None)

    assert forgot(client, student.mobile).status_code == 200

    resp = verify(client, student.mobile)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ADMIN_RESET_REQUIRED"
    assert resp.json()["detail"]["message"] == ADMIN_HELP


# ---------------------------------------------------------------------------
# Step 3 - reset password
# ---------------------------------------------------------------------------


def test_reset_rejects_weak_and_reused_passwords(client, db, monkeypatch):
    mail_ok(monkeypatch)
    no_rate_cap(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    def _token():
        forgot(client, user.mobile)
        resp = verify(client, user.mobile)
        assert resp.status_code == 200, resp.text
        return resp.json()["reset_token"]

    weak_cases = {
        "short1A": "Password must be at least 8 characters long.",
        "alllowercase1": "Password must contain at least one uppercase letter.",
        "ALLUPPERCASE1": "Password must contain at least one lowercase letter.",
        "NoDigitsHere": "Password must contain at least one digit.",
        "Principal@123": "This password is not allowed. Please choose a different one.",
        DEFAULT_PASSWORD: "New password must be different from your current password.",
    }
    for candidate, expected in weak_cases.items():
        resp = complete(client, _token(), password=candidate)
        assert resp.status_code == 400, (candidate, resp.text)
        assert resp.json()["detail"]["code"] == "WEAK_PASSWORD"
        assert resp.json()["detail"]["message"] == expected
        # Nothing was changed and the token survived (nothing was burned).
        login(client, user.mobile)

    # The final, compliant password works and revokes the live session.
    live = login(client, user.mobile)
    good = complete(client, _token(), password="FreshPass456!")
    assert good.status_code == 200
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(live["access_token"])).status_code == 401
    login(client, user.mobile, password="FreshPass456!")
    assert (
        client.post(
            f"{PREFIX}/auth/login",
            json={"mobile": user.mobile, "password": DEFAULT_PASSWORD},
        ).status_code
        == 401
    )

    logs = db.query(AuditLog).filter(AuditLog.action == "PASSWORD_RESET").all()
    assert len(logs) == 1
    assert logs[0].resource_id == str(user.id)
    assert logs[0].details == {"method": "otp_email"}


def test_reset_password_with_bogus_token_is_rejected(client, db):
    resp = complete(client, "bogus-token")
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "RESET_TOKEN_INVALID"


def test_completed_reset_closes_a_pending_admin_request(client, db, monkeypatch):
    mail_ok(monkeypatch)
    school = make_school(db)
    user = make_user(db, school, role="STUDENT", email=None)

    # No email -> staff queue.
    forgot(client, user.mobile)
    assert db.query(PasswordResetRequest).filter(PasswordResetRequest.status == "pending").count() == 1

    # Mail later works (address added by an admin) -> self service succeeds.
    user.email = "student@example.com"
    db.add(user)
    db.commit()
    forgot(client, user.mobile)
    token = verify(client, user.mobile).json()["reset_token"]
    assert complete(client, token).status_code == 200

    request = db.query(PasswordResetRequest).filter(PasswordResetRequest.user_id == user.id).one()
    assert request.status == "completed"


# ---------------------------------------------------------------------------
# Flow B - admin assisted
# ---------------------------------------------------------------------------


def _admin_reset(client, admin_token: str, user_id: int):
    return client.post(
        f"{PREFIX}/admin/users/{user_id}/reset-password",
        headers=bearer(admin_token),
    )


def test_admin_reset_issues_one_time_password_and_forces_change(client, db):
    school = make_school(db)
    principal = make_user(db, school, role="PRINCIPAL")
    student = make_user(db, school, role="STUDENT", email=None)
    live = login(client, student.mobile)
    admin = login(client, principal.mobile)

    forgot(client, student.mobile)  # creates the pending request

    resp = _admin_reset(client, admin["access_token"], student.id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    temp = body["temporary_password"]
    assert body["must_change_password"] is True
    assert len(temp) >= 8 and any(c.isupper() for c in temp)
    assert any(c.islower() for c in temp) and any(c.isdigit() for c in temp)

    # Only the bcrypt hash is persisted - the temp password is never stored.
    db.refresh(student)
    from app.core.security import verify_password

    assert verify_password(temp, student.password_hash)
    assert temp not in student.password_hash

    # Live sessions are dead immediately and the queue entry is closed.
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(live["access_token"])).status_code == 401
    assert db.query(RefreshToken).filter(RefreshToken.user_id == student.id).count() >= 1
    request = db.query(PasswordResetRequest).filter(PasswordResetRequest.user_id == student.id).one()
    assert request.status == "completed"
    assert request.handled_by == principal.id

    # The student signs in with the temp password and MUST change it.
    forced = login(client, student.mobile, password=temp)
    assert forced["must_change_password"] is True

    changed = client.post(
        f"{PREFIX}/auth/change-password",
        headers=bearer(forced["access_token"]),
        json={"current_password": temp, "new_password": "BrandNew456!"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False

    # The temp password is single-use too.
    assert (
        client.post(
            f"{PREFIX}/auth/login",
            json={"mobile": student.mobile, "password": temp},
        ).status_code
        == 401
    )

    logs = db.query(AuditLog).filter(AuditLog.action == "RESET_PASSWORD").all()
    assert len(logs) == 1
    assert logs[0].user_id == principal.id
    assert logs[0].resource_id == str(student.id)


def test_principal_scope_is_tenant_and_role_checked(client, db, world):
    school_a, school_b = world.a.school, world.b.school
    principal = make_user(db, school_a, role="PRINCIPAL")
    teacher_of_a = make_user(db, school_a, role="TEACHER")
    student_of_a = make_user(db, school_a, role="STUDENT", email=None)
    principal_of_a = make_user(db, school_a, role="PRINCIPAL")
    teacher_of_b = make_user(db, school_b, role="TEACHER")
    admin = login(client, principal.mobile)

    # In scope: their own school's teachers and students.
    for target in (teacher_of_a, student_of_a):
        assert _admin_reset(client, admin["access_token"], target.id).status_code == 200

    # Out of scope: another school, and a fellow Principal.
    for target in (teacher_of_b, principal_of_a):
        resp = _admin_reset(client, admin["access_token"], target.id)
        assert resp.status_code == 403, target.role
        assert resp.json()["detail"]["code"] == "FORBIDDEN_ROLE"


def test_teacher_can_never_reset_anyone(client, db):
    school = make_school(db)
    teacher = make_user(db, school, role="TEACHER")
    victim = make_user(db, school, role="STUDENT", email=None)
    session = login(client, teacher.mobile)

    resp = _admin_reset(client, session["access_token"], victim.id)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Operation not permitted for this user role"

    # Listing and rejecting are equally closed.
    listing = client.get(f"{PREFIX}/admin/password-reset-requests", headers=bearer(session["access_token"]))
    assert listing.status_code == 403


def test_super_admin_handles_principals_and_sees_every_request(client, db, world):
    school_a, school_b = world.a.school, world.b.school
    principal_of_a = make_user(db, school_a, role="PRINCIPAL")
    principal_of_b = make_user(db, school_b, role="PRINCIPAL")
    # Queue an entry for a Principal: only Super Admin may see/handle it.
    password_reset_service.ensure_admin_request(db, principal_of_b)
    superadmin = login(client, world.superadmin.mobile)

    assert _admin_reset(client, superadmin["access_token"], principal_of_a.id).status_code == 200
    assert _admin_reset(client, superadmin["access_token"], principal_of_b.id).status_code == 200

    listing = client.get(
        f"{PREFIX}/admin/password-reset-requests?status=all",
        headers=bearer(superadmin["access_token"]),
    )
    assert listing.status_code == 200
    seen_roles = {row["role"] for row in listing.json()}
    assert "PRINCIPAL" in seen_roles


def test_principal_request_list_only_contains_their_teachers_and_students(client, db, world):
    school_a, school_b = world.a.school, world.b.school
    principal = make_user(db, school_a, role="PRINCIPAL")
    student_a = make_user(db, school_a, role="STUDENT", email=None)
    teacher_b = make_user(db, school_b, role="TEACHER")
    # Queue one request per account, bypassing the mail path.
    password_reset_service.ensure_admin_request(db, student_a)
    password_reset_service.ensure_admin_request(db, teacher_b)

    session = login(client, principal.mobile)
    listing = client.get(f"{PREFIX}/admin/password-reset-requests", headers=bearer(session["access_token"]))
    assert listing.status_code == 200
    rows = listing.json()
    assert [row["user_id"] for row in rows] == [student_a.id]
    assert rows[0]["status"] == "pending"
    assert rows[0]["has_email"] is False


def test_rejecting_a_request_never_changes_the_password(client, db):
    school = make_school(db)
    principal = make_user(db, school, role="PRINCIPAL")
    student = make_user(db, school, role="STUDENT", email=None)
    request = password_reset_service.ensure_admin_request(db, student)
    session = login(client, principal.mobile)

    resp = client.post(
        f"{PREFIX}/admin/password-reset-requests/{request.id}/reject",
        headers=bearer(session["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    db.refresh(student)
    from app.core.security import verify_password

    assert verify_password(DEFAULT_PASSWORD, student.password_hash)

    # A rejected request cannot be handled twice.
    again = client.post(
        f"{PREFIX}/admin/password-reset-requests/{request.id}/reject",
        headers=bearer(session["access_token"]),
    )
    assert again.status_code == 400
    assert again.json()["detail"]["code"] == "ALREADY_HANDLED"


def test_unauthenticated_caller_cannot_touch_admin_endpoints(client, db):
    assert client.get(f"{PREFIX}/admin/password-reset-requests").status_code in (401, 403)
    assert client.post(f"{PREFIX}/admin/users/1/reset-password").status_code in (401, 403)


def test_smtp_settings_are_declared_and_the_gate_behaves(monkeypatch):
    """``smtp_configured()`` reads ``SMTP_HOST`` and ``MAIL_FROM`` unguarded.

    If either attribute is missing from ``Settings`` the failure is an
    AttributeError raised *inside the request* - a 500 on
    ``POST /auth/forgot-password`` that the suite cannot see, because an empty
    ``SMTP_HOST`` short-circuits the ``and`` and the attribute is never read.
    Only a configured (i.e. production) SMTP ever reaches it.
    """
    from app.core import mailer
    from app.core.config import settings

    for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"):
        assert hasattr(settings, name), f"Settings.{name} is missing"

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "MAIL_FROM", "noreply@example.com")
    assert mailer.smtp_configured() is True

    monkeypatch.setattr(settings, "MAIL_FROM", "")
    assert mailer.smtp_configured() is False
    # Never raises, never sends: a delivery failure is a boolean.
    assert mailer.send_mail(to="someone@example.com", subject="s", body="b") is False

    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "MAIL_FROM", "noreply@example.com")
    assert mailer.smtp_configured() is False
