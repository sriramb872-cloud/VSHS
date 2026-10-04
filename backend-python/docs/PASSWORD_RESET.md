# Password Reset

Two recovery paths, both reachable from **"Forgot password?"** on the sign-in
screen (`/forgot-password`):

| | Flow A — self service | Flow B — admin assisted |
|---|---|---|
| Who | Account with a deliverable email | No email on file (mainly students), or mail delivery failed |
| Steps | login ID → 6-digit code by email → new password | user asks staff → Principal/Super Admin issues a one-time temporary password → user must change it at next sign-in |
| Endpoints | `POST /auth/forgot-password`, `POST /auth/verify-reset-otp`, `POST /auth/reset-password` | `GET /admin/password-reset-requests`, `POST /admin/users/{id}/reset-password`, `POST /admin/password-reset-requests/{id}/reject` |

There is no Parent role in SCHOLARIS, so Flow B is a staff action:

| Actor | May reset |
|---|---|
| Super Admin | anyone, across schools |
| Principal | Teachers and Students **of their own school** |
| Teacher | nobody (the role is absent from `require_roles`) |

The hierarchy and the tenant check are enforced **server-side** in
`app/routers/v1/admin_password_reset.py::_ensure_may_manage`, never on the
client's word.

## Security properties

* **No enumeration.** `POST /auth/forgot-password` always answers the same
  200 body — `{"message": "If an account exists, a code has been sent.",
  "expires_in_minutes": 10}` — whether the login ID is unknown, deactivated,
  has no email, or was just mailed. The response is byte-identical.
* **Codes are never stored or logged in the clear.** `password_reset_otps`
  keeps an HMAC-SHA256 keyed with `SECRET_KEY` and bound to the owning user
  id; the same row later keeps the SHA-256 of the single-use reset token.
* **Short-lived and single-use.** Code: 10 minutes, 5 wrong attempts (then it
  locks). Reset token: 10 minutes, spent by `reset-password`, unusable after.
* **The reset token is returned only by `verify-reset-otp`** — to the caller
  who just proved the code — and nowhere else. The retired endpoint that
  returned a reset token to anyone who asked has been removed.
* **Password policy** on the new password: ≥8 characters with an uppercase
  letter, a lowercase letter and a digit; shipped defaults
  (`Principal@123`, `Password@123`, `Admin@123`) and the account's current
  password are rejected.
* **A completed reset revokes every session** of that account (access *and*
  refresh tokens) and writes an `audit_logs` row.
* **Rate limits:** 5/hour per IP *and* 5/hour per login ID for
  `forgot-password`; 60/hour (verify) and 30/hour (reset) per IP. The
  per-IP limits are slowapi (HTTP 429); the per-login-ID cap is counted in
  the database so it holds across workers and is enforced silently (the
  generic response is returned either way).
* **Errors carry a stable code** so the UI never parses prose:

  | `detail.code` | Meaning |
  |---|---|
  | `INVALID_OTP` | wrong code, unknown login ID, or no outstanding code |
  | `OTP_EXPIRED` | code is older than `OTP_TTL_MINUTES` |
  | `OTP_LOCKED` | `OTP_MAX_ATTEMPTS` wrong tries |
  | `ADMIN_RESET_REQUIRED` (403) | no deliverable email → show the "contact your Principal" message |
  | `RESET_TOKEN_INVALID` | token spent, unknown or expired |
  | `WEAK_PASSWORD` | new password fails the policy |
  | `FORBIDDEN_ROLE` | actor may not reset that account |
  | `ALREADY_HANDLED` | request was completed/rejected already |

  Every reset error is `detail = {"message": ..., "code": ...}`.

* **SMTP down ≠ dead end.** If mail cannot be sent (server error *or* SMTP
  never configured) the code is retired immediately and a Flow B request is
  queued, so the account always has a route back in.

## Configuration

See the table in `docs/DEPLOYMENT.md`. In short, self-service needs
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`; the
timings/limits come from `OTP_TTL_MINUTES`, `OTP_MAX_ATTEMPTS`,
`RESET_TOKEN_TTL_MINUTES`, `FORGOT_PASSWORD_PER_HOUR`.

## Database

Two ways to apply the schema — **use one, not both**:

```bash
alembic upgrade head                  # normal path: run by start.sh on deploy
```

```bash
# manual path (only when applying schema changes by hand)
mysql -u root -p vshs_db < password_reset_migration.sql
```

Adds `password_reset_otps`, `password_reset_requests` and (only when missing)
`users.must_change_password`. Revision `alembic/versions/0005_password_reset.py`
and `password_reset_migration.sql` are mirrors: both are existence-guarded, so
running either twice — or both on the same database — is a no-op. The SQL file
was validated against a disposable MySQL database: after it creates the two
tables, `alembic check` reports *"No new upgrade operations detected"*.

## Frontend

| Route | Screen |
|---|---|
| `/forgot-password` | 3-step flow: login ID → 6-digit code (60-second resend timer) → new password with a live policy checklist; success screen at the end |
| login screen | **Forgot password?** link under the password field |
| login screen (after an admin reset) | forced change-password screen with show/hide and the same checklist |
| `/superadmin/password-reset-requests`, `/principal/password-reset-requests` | Flow B queue: Pending/Completed/Rejected/All, **Reset** (shows the temporary password once, blurred until revealed, with copy) and **Reject** |

The temporary password is held in component state only, never persisted, and
dropped as soon as the dialog is closed.

## Manual test checklist

Run against a staging environment with SMTP configured (or accept the Flow B
fallback where it is not).

### Flow A — self service

1. **Link present** — `/login` shows *Forgot password?* under the password
   field; `/forgot-password` renders the same dark-gradient card as login.
2. **Unknown login ID** — submit a random ID: the message is exactly
   *"If an account exists, a code has been sent."* and the screen advances to
   the code step. It must be **identical** to the message for a real account.
3. **Real account** — the code arrives by email; no OTP appears in any API
   response, server log or `audit_logs`.
4. **Wrong code ×5** — after the 5th attempt the code locks
   (*"Too many incorrect attempts…"*) and a resend is required; a correct code
   entered afterwards no longer works for the spent code.
5. **Expired code** — wait past `OTP_TTL_MINUTES` (default 10): verify returns
   `OTP_EXPIRED`; the UI offers a resend.
6. **Resend timer** — *Resend code* is disabled with a 60-second countdown
   after each send, then re-enables.
7. **Weak password** — `password`, `principal@123`, `Password@123` or a
   password without a digit are refused with `WEAK_PASSWORD`; the checklist
   ticks live as you type.
8. **Reuse / replay** — a reset token cannot be spent twice: completing the
   reset and then re-posting the same token returns `RESET_TOKEN_INVALID`.
9. **Old sessions die** — sign in on a second device, complete a reset on the
   first, then reload the second: the old refresh token is revoked and the app
   returns to `/login`.
10. **Rate limit (per IP)** — hit `forgot-password` 6 times from one IP within
    an hour: the 6th returns HTTP 429 (slowapi) and the UI says *Too many
    attempts*; no code is sent.
11. **Rate limit (per login ID)** — 5 requests for one login ID, then further
    requests from a different IP still return the generic message but send
    nothing.
12. **Admin-help branch** — an account with no email (or SMTP switched off)
    advances to the code step with the generic message, and verification then
    returns 403 `ADMIN_RESET_REQUIRED`: the UI shows *"Please contact your
    Principal or class teacher to reset your password."* and stops.

### Flow B — admin assisted

13. **Student with no email** — after step 12 a `pending` row appears in
    *Password Reset Requests* for a Principal of that school (and for Super
    Admin).
14. **Principal scope** — a Principal sees only Teachers/Students of their own
    school; a Super Admin sees every request.
15. **Reset** — confirm the dialog: the temporary password is shown **once**,
    blurred until *Show*, copyable; `users.must_change_password` is now true
    and every session of that user is revoked.
16. **Teacher cannot reset** — calling `POST /admin/users/{id}/reset-password`
    with a Teacher token returns 403.
17. **Cross-school** — a Principal resetting a user of another school returns
    403 `FORBIDDEN_ROLE` and nothing changes.
18. **Forced change** — sign in with the temporary password: the change
    screen appears before any dashboard, and the new password must satisfy the
    same policy; afterwards `must_change_password` is false.
19. **Reject** — *Reject* marks the row `rejected` (visible under the Rejected
    filter), the password is untouched, and an `audit_logs` row exists for
    both reset and reject with `action=RESET_PASSWORD` / `PASSWORD_RESET_REJECTED`.

### Regression

20. `/forgot-password` deep-links correctly on a hard refresh in production
    (`frontend/vercel.json` rewrites `/(.*)` → `/index.html`).
21. Login still works normally afterwards, and the old
    `POST /users/{id}/reset-password` endpoint (client-supplied password) is
    unchanged for existing callers.
22. `pytest -q` is green (`tests/test_password_reset.py`, `tests/test_auth.py`)
    and `ruff check .` reports nothing new.
