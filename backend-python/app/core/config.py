import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be an integer, got: {raw!r}")


def _str_env(name: str) -> Optional[str]:
    """Optional string setting: unset and blank both mean "not configured"."""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip()


def _bool_env(name: str, default: bool) -> bool:
    """Optional boolean setting: unset means ``default``."""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    DATABASE_URL: str = os.environ["DATABASE_URL"]

    SECRET_KEY: str = os.environ["SECRET_KEY"]

    ALGORITHM: str = os.getenv(
        "ALGORITHM",
        "HS256",
    )

    # Access tokens are deliberately short-lived. Clients obtain a fresh
    # access token by presenting their refresh token to POST /auth/refresh,
    # so a stolen access token expires quickly even if it is never revoked.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _int_env(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        30,
    )

    # Refresh tokens live longer (they are the "session") but are stored
    # server-side (hashed), rotatable and revocable.
    REFRESH_TOKEN_EXPIRE_DAYS: int = _int_env(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        14,
    )

    # Per-account brute-force protection. Deliberately per *account* (never
    # per school or per network) and time-boxed, so a lockout cannot take out
    # a whole school behind a shared NAT address.
    LOGIN_MAX_FAILED_ATTEMPTS: int = _int_env(
        "LOGIN_MAX_FAILED_ATTEMPTS",
        10,
    )
    LOGIN_LOCKOUT_MINUTES: int = _int_env(
        "LOGIN_LOCKOUT_MINUTES",
        15,
    )

    # --- Password reset (Flow A: self-service OTP delivered by email) -------
    # The OTP and the single-use reset token are both short-lived: a code that
    # sits in an inbox for hours is a code an attacker can wait for.
    OTP_TTL_MINUTES: int = _int_env("OTP_TTL_MINUTES", 10)
    RESET_TOKEN_TTL_MINUTES: int = _int_env("RESET_TOKEN_TTL_MINUTES", 10)
    # Wrong OTP attempts allowed per code before it is invalidated.
    OTP_MAX_ATTEMPTS: int = _int_env("OTP_MAX_ATTEMPTS", 5)
    # Self-service reset requests per hour PER LOGIN ID (the per-IP bucket is
    # enforced separately by slowapi). Counted from the database, so it holds
    # across every gunicorn worker.
    FORGOT_PASSWORD_PER_HOUR: int = _int_env("FORGOT_PASSWORD_PER_HOUR", 5)

    # --- SMTP (any provider: Gmail app password, Brevo, Resend, ...) --------
    # Never committed: production values live in the Railway environment.
    # MAIL_FROM is read unguarded by app.core.mailer.smtp_configured(), so it
    # must stay declared here (an SMTP_HOST without MAIL_FROM simply means
    # "not configured").
    SMTP_HOST: Optional[str] = _str_env("SMTP_HOST")
    SMTP_PORT: int = _int_env("SMTP_PORT", 587)
    SMTP_USER: Optional[str] = _str_env("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = _str_env("SMTP_PASSWORD")
    MAIL_FROM: Optional[str] = _str_env("MAIL_FROM")
    # --- Payments (Razorpay = real UPI checkout, ORDERS API) ---------------
    # "INTERNAL" -> development-only mock provider (never usable in
    #               production - see PaymentService.mock_payments_enabled).
    # "RAZORPAY"  -> real one-time prepaid UPI payments through Razorpay.
    PAYMENT_PROVIDER: str = (os.getenv("PAYMENT_PROVIDER") or "INTERNAL").strip().upper()

    # The key_id is PUBLIC (the browser needs it to open Checkout.js); the key
    # secret and the webhook secret stay server-side only - never logged,
    # never serialised into a response, never committed.
    RAZORPAY_KEY_ID: Optional[str] = _str_env("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: Optional[str] = _str_env("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = _str_env("RAZORPAY_WEBHOOK_SECRET")

    # --- Web Push (VAPID) -----------------------------------------------------
    # Optional. Generate a key pair with:
    #   python -m py_vapid --gen --version2 --applicationServerKey
    # and paste the printed values below. The app boots fine with none of
    # these set: PUSH_ENABLED then defaults to False and every push code
    # path is a no-op.
    VAPID_PUBLIC_KEY: Optional[str] = _str_env("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY: Optional[str] = _str_env("VAPID_PRIVATE_KEY")
    # VAPID contact claim (mailto: or https:). Required by the Web Push
    # protocol when sending; defaults to a placeholder you should replace.
    VAPID_SUBJECT: str = _str_env("VAPID_SUBJECT") or "mailto:admin@example.com"
    # Defaults to True only when BOTH VAPID keys are configured.
    PUSH_ENABLED: bool = _bool_env(
        "PUSH_ENABLED",
        default=bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY),
    )


settings = Settings()

# The Razorpay values that must exist once Razorpay is the live provider.
RAZORPAY_REQUIRED_SETTINGS = (
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET",
)


def validate_payment_settings(
    *, environment: Optional[str] = None, provider: Optional[str] = None
) -> None:
    """Fail fast when Razorpay is selected without its credentials.

    Runs at import time (== application startup) and is also callable with
    explicit values so tests do not have to re-import the module. Only the
    NAMES of the missing variables are reported - never their values, so no
    secret can end up in a log or a traceback.
    """
    env = (
        environment if environment is not None else os.getenv("ENVIRONMENT", "")
    ).strip().lower()
    active = (
        provider if provider is not None else settings.PAYMENT_PROVIDER
    ).strip().upper()
    if env != "production" or active != "RAZORPAY":
        return
    missing = [name for name in RAZORPAY_REQUIRED_SETTINGS if not getattr(settings, name)]
    if missing:
        raise RuntimeError(
            "PAYMENT_PROVIDER=RAZORPAY in production requires "
            + ", ".join(missing)
            + " to be set (placeholders live in .env.example)."
        )


# Startup check: a production deployment that selected Razorpay without its
# secrets must not boot into a state where every checkout silently fails.
validate_payment_settings()
