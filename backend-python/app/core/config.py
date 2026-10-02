import os

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


settings = Settings()
