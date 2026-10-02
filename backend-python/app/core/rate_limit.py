import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


# Per-IP rate limiting (slowapi) is the *first* line of defence; per-account
# lockout (auth_service) is separate and never disabled by this flag.
# Set RATE_LIMIT_ENABLED=false only for local debugging - keep it on in
# production.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=_flag("RATE_LIMIT_ENABLED", True),
    default_limits=[],  # endpoints declare their own limits explicitly
)
