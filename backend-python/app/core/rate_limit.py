import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def client_ip_key(request: Request) -> str:
    """Rate-limit key for endpoints that sit behind a reverse proxy.

    ``slowapi.util.get_remote_address`` only reads ``request.client.host``.
    Behind Railway (or any proxy) that is the *proxy's* address, which would
    collapse every user of a school into ONE bucket and rate-limit the whole
    campus after five requests.

    So the right-most ``X-Forwarded-For`` entry is preferred: it is the address
    the trusted proxy appended, so a client cannot spoof its way past the limit
    by sending its own header (only the proxy's append survives the "last
    entry" rule).

    This key is only ever one of two defenses. The authoritative per-account
    limit (5 forgot-password requests / hour / login ID) is counted in the
    database and does not depend on any header at all.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        last_hop = forwarded.split(",")[-1].strip()
        if last_hop:
            return last_hop
    if request.client and request.client.host:
        return request.client.host
    return get_remote_address(request)


# Per-IP rate limiting (slowapi) is the *first* line of defence; per-account
# lockout (auth_service) is separate and never disabled by this flag.
# Set RATE_LIMIT_ENABLED=false only for local debugging - keep it on in
# production.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=_flag("RATE_LIMIT_ENABLED", True),
    default_limits=[],  # endpoints declare their own limits explicitly
)
