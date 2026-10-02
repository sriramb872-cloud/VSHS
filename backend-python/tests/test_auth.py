"""Authentication & session-security regression tests.

Covers: login identifiers, short-lived access tokens, rotating (single-use)
refresh tokens, replay detection, server-side revocation, token-version
invalidation, forced password change, per-account lockout, inactive accounts,
reset flow, and account-enumeration resistance.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.core.token_service import hash_refresh_token
from app.models.refresh_token import RefreshToken
from tests.factories import (  # noqa: F401  (``db``/``client`` come from conftest)
    DEFAULT_PASSWORD,
    make_school,
    make_student,
    make_user,
)

PREFIX = "/api/v1"


def login(client, identifier: str, password: str = DEFAULT_PASSWORD):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": identifier, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def refresh(client, raw_token: str):
    return client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": raw_token})


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_returns_short_lived_access_and_refresh_pair(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    tokens = login(client, user.mobile)

    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    # Access token lifetime comes from ACCESS_TOKEN_EXPIRE_MINUTES (30 min),
    # refresh token lifetime from REFRESH_TOKEN_EXPIRE_DAYS (14 days).
    assert tokens["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert tokens["refresh_token_expires_in"] == settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    assert tokens["must_change_password"] is False

    me = client.get(f"{PREFIX}/auth/me", headers=bearer(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["id"] == user.id
    assert me.json()["mobile"] == user.mobile


def test_login_response_never_leaks_password_hash(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": user.mobile, "password": DEFAULT_PASSWORD},
    )
    assert resp.status_code == 200
    assert "$2b$" not in resp.text
    assert DEFAULT_PASSWORD not in resp.text


def test_login_rejects_wrong_password(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": user.mobile, "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert "access_token" not in resp.json()


def test_login_accepts_admission_number_for_students(client, db):
    school = make_school(db)
    student = make_student(db, school)

    tokens = login(client, student.admission_number)

    me = client.get(f"{PREFIX}/auth/me", headers=bearer(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "STUDENT"
    assert me.json()["id"] == student.user_id


def test_login_by_unknown_identifier_is_401(client, db):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": "0000000000", "password": DEFAULT_PASSWORD},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Access token validation
# ---------------------------------------------------------------------------


def test_token_without_version_claim_is_rejected(client, db):
    """Tokens minted without the ``tv`` claim (legacy/crafted) must fail."""
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    legacy = create_access_token(
        data={"sub": str(user.id), "role": user.role, "school_id": user.school_id}
    )
    resp = client.get(f"{PREFIX}/auth/me", headers=bearer(legacy))
    assert resp.status_code == 401


def test_token_with_wrong_version_claim_is_rejected(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    forged = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "school_id": user.school_id,
            "tv": int(user.token_version) + 7,
        }
    )
    resp = client.get(f"{PREFIX}/auth/me", headers=bearer(forged))
    assert resp.status_code == 401


def test_expired_access_token_is_rejected(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    expired = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "school_id": user.school_id,
            "tv": int(user.token_version),
        },
        expires_delta=timedelta(seconds=-5),
    )
    resp = client.get(f"{PREFIX}/auth/me", headers=bearer(expired))
    assert resp.status_code == 401


def test_tampered_token_is_rejected(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    tokens = login(client, user.mobile)
    tampered = tokens["access_token"][:-3] + ("aaa" if not tokens["access_token"].endswith("aaa") else "bbb")
    resp = client.get(f"{PREFIX}/auth/me", headers=bearer(tampered))
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh-token rotation & revocation
# ---------------------------------------------------------------------------


def test_refresh_rotates_token_and_rejects_replay(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    first = login(client, user.mobile)

    second = refresh(client, first["refresh_token"])
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["refresh_token"] != first["refresh_token"]

    # Replaying the consumed (stolen) token must fail.
    replay = refresh(client, first["refresh_token"])
    assert replay.status_code == 401

    # The rotated token keeps working...
    third = refresh(client, second_body["refresh_token"])
    assert third.status_code == 200

    # ...and the original access token remains valid until it expires
    # (rotation only invalidates the refresh token that was presented).
    me = client.get(f"{PREFIX}/auth/me", headers=bearer(first["access_token"]))
    assert me.status_code == 200


def test_unknown_refresh_token_is_rejected(client, db):
    resp = refresh(client, "not-a-real-token")
    assert resp.status_code == 401


def test_expired_refresh_token_is_rejected(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    tokens = login(client, user.mobile)

    row = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == hash_refresh_token(tokens["refresh_token"])
        )
        .one()
    )
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    assert refresh(client, tokens["refresh_token"]).status_code == 401


def test_logout_revokes_only_that_session(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    session_a = login(client, user.mobile)
    session_b = login(client, user.mobile)

    out = client.post(f"{PREFIX}/auth/logout", json={"refresh_token": session_a["refresh_token"]})
    assert out.status_code == 200

    assert refresh(client, session_a["refresh_token"]).status_code == 401
    # The other session is untouched.
    assert refresh(client, session_b["refresh_token"]).status_code == 200


def test_logout_is_idempotent_for_unknown_tokens(client, db):
    resp = client.post(f"{PREFIX}/auth/logout", json={"refresh_token": "unknown"})
    assert resp.status_code == 200

    resp_none = client.post(f"{PREFIX}/auth/logout", json={})
    assert resp_none.status_code == 200


def test_logout_all_invalidates_every_session_instantly(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    session_a = login(client, user.mobile)
    session_b = login(client, user.mobile)

    resp = client.post(
        f"{PREFIX}/auth/logout-all",
        headers=bearer(session_a["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["sessions_revoked"] >= 2

    # Every outstanding access token dies immediately (token version bump)...
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(session_a["access_token"])).status_code == 401
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(session_b["access_token"])).status_code == 401
    # ...and so do all refresh tokens.
    assert refresh(client, session_a["refresh_token"]).status_code == 401
    assert refresh(client, session_b["refresh_token"]).status_code == 401

    # A fresh login still works.
    fresh = login(client, user.mobile)
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(fresh["access_token"])).status_code == 200


# ---------------------------------------------------------------------------
# Password change / reset
# ---------------------------------------------------------------------------


def test_change_password_wrong_current_password(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    tokens = login(client, user.mobile)

    resp = client.post(
        f"{PREFIX}/auth/change-password",
        headers=bearer(tokens["access_token"]),
        json={"current_password": "not-the-password", "new_password": "NewSecret456!"},
    )
    assert resp.status_code == 400
    # Nothing changed: old password still works.
    login(client, user.mobile)


def test_change_password_returns_fresh_pair_and_kills_old_sessions(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    old = login(client, user.mobile)
    other_device = login(client, user.mobile)

    resp = client.post(
        f"{PREFIX}/auth/change-password",
        headers=bearer(old["access_token"]),
        json={"current_password": DEFAULT_PASSWORD, "new_password": "NewSecret456!"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["message"]
    assert body["access_token"] and body["refresh_token"]
    assert body["must_change_password"] is False

    # Old sessions (this device AND any other device) are dead.
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(old["access_token"])).status_code == 401
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(other_device["access_token"])).status_code == 401
    assert refresh(client, old["refresh_token"]).status_code == 401
    assert refresh(client, other_device["refresh_token"]).status_code == 401

    # The returned pair keeps the current flow alive.
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(body["access_token"])).status_code == 200
    assert refresh(client, body["refresh_token"]).status_code == 200

    # Credentials actually rotated.
    assert client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": user.mobile, "password": DEFAULT_PASSWORD},
    ).status_code == 401
    assert client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": user.mobile, "password": "NewSecret456!"},
    ).status_code == 200


def test_must_change_password_flag_is_cleared_by_change(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER", must_change_password=True)

    forced = login(client, user.mobile)
    assert forced["must_change_password"] is True

    resp = client.post(
        f"{PREFIX}/auth/change-password",
        headers=bearer(forced["access_token"]),
        json={"current_password": DEFAULT_PASSWORD, "new_password": "NewSecret456!"},
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is False

    relogin = login(client, user.mobile, password="NewSecret456!")
    assert relogin["must_change_password"] is False


def test_admin_reset_revokes_sessions_and_rotates_password(client, db):
    school = make_school(db)
    principal = make_user(db, school, role="PRINCIPAL")
    victim = make_user(db, school, role="TEACHER")
    victim_session = login(client, victim.mobile)
    admin_session = login(client, principal.mobile)

    resp = client.post(
        f"{PREFIX}/users/{victim.id}/reset-password",
        headers=bearer(admin_session["access_token"]),
        json={"password": "TempPass123!"},
    )
    assert resp.status_code == 200, resp.text

    # Victim's live sessions are gone; new credentials force a change next login.
    assert refresh(client, victim_session["refresh_token"]).status_code == 401
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(victim_session["access_token"])).status_code == 401

    relogin = login(client, victim.mobile, password="TempPass123!")
    assert relogin["must_change_password"] is True


def test_reset_password_flow_revokes_existing_sessions(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    live = login(client, user.mobile)

    forgot = client.post(f"{PREFIX}/auth/forgot-password", json={"mobile": user.mobile})
    assert forgot.status_code == 200

    db.refresh(user)
    reset_token = user.reset_token
    assert reset_token  # stored server-side; delivery channel is out of scope

    resp = client.post(
        f"{PREFIX}/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "ResetPass789!"},
    )
    assert resp.status_code == 200

    assert refresh(client, live["refresh_token"]).status_code == 401
    assert client.get(f"{PREFIX}/auth/me", headers=bearer(live["access_token"])).status_code == 401
    login(client, user.mobile, password="ResetPass789!")

    # Single-use: the same token cannot be replayed.
    replay = client.post(
        f"{PREFIX}/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "AnotherPass1!"},
    )
    assert replay.status_code == 400


def test_forgot_password_response_is_identical_for_known_and_unknown(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")

    known = client.post(f"{PREFIX}/auth/forgot-password", json={"mobile": user.mobile})
    unknown = client.post(f"{PREFIX}/auth/forgot-password", json={"mobile": "9999999999"})

    assert known.status_code == unknown.status_code
    assert known.json() == unknown.json()


def test_reset_password_with_bogus_token_is_rejected(client, db):
    resp = client.post(
        f"{PREFIX}/auth/reset-password",
        json={"reset_token": "bogus", "new_password": "Whatever123!"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Account state: lockout & deactivation
# ---------------------------------------------------------------------------


def test_account_lockout_is_per_account_and_time_boxed(client, db):
    school = make_school(db)
    victim = make_user(db, school, role="TEACHER")
    neighbour = make_user(db, school, role="TEACHER")
    neighbour_session = login(client, neighbour.mobile)

    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        resp = client.post(
            f"{PREFIX}/auth/login",
            json={"mobile": victim.mobile, "password": "wrong-password"},
        )
        assert resp.status_code == 401

    db.refresh(victim)
    assert victim.locked_until is not None

    # Even the CORRECT password fails while locked, and the response is the
    # same plain 401 (no lock disclosure).
    locked = client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": victim.mobile, "password": DEFAULT_PASSWORD},
    )
    assert locked.status_code == 401

    # Lockout is per account: another account of the SAME school is unaffected.
    neighbour_check = client.get(
        f"{PREFIX}/auth/me", headers=bearer(neighbour_session["access_token"])
    )
    assert neighbour_check.status_code == 200
    assert refresh(client, neighbour_session["refresh_token"]).status_code == 200

    # Lockout is time-boxed: once it expires, the account recovers.
    victim.locked_until = datetime.utcnow() - timedelta(minutes=1)
    victim.failed_login_attempts = 0
    db.commit()

    recovered = client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": victim.mobile, "password": DEFAULT_PASSWORD},
    )
    assert recovered.status_code == 200
    db.refresh(victim)
    assert victim.locked_until is None
    assert victim.failed_login_attempts == 0


def test_inactive_account_cannot_login_or_use_existing_tokens(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    tokens = login(client, user.mobile)

    user.is_active = "INACTIVE"
    db.commit()

    assert client.post(
        f"{PREFIX}/auth/login",
        json={"mobile": user.mobile, "password": DEFAULT_PASSWORD},
    ).status_code == 401

    me = client.get(f"{PREFIX}/auth/me", headers=bearer(tokens["access_token"]))
    assert me.status_code == 403
    assert me.json()["detail"] == "Inactive user account"


def test_refresh_for_inactive_account_is_rejected(client, db):
    school = make_school(db)
    user = make_user(db, school, role="TEACHER")
    tokens = login(client, user.mobile)

    user.is_active = "INACTIVE"
    db.commit()

    assert refresh(client, tokens["refresh_token"]).status_code == 401


def test_rate_limit_flag_is_environment_driven():
    """``RATE_LIMIT_ENABLED=false`` must disable slowapi (CI/local runs);
    per-account lockout above stays active regardless of this flag."""
    assert limiter.enabled is False
