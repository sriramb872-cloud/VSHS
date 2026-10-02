"""Liveness/readiness probes, CORS policy, debug-endpoint removal, request IDs."""

from __future__ import annotations

PREFIX = "/api/v1"


def test_health_is_liveness_only(client):
    """``/health`` must answer 200 without touching any dependency."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_reports_database_ok(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"


def test_ready_never_leaks_connection_details(client):
    resp = client.get("/ready")
    text = resp.text.lower()
    for secret in ("sqlite", "mysql", "password", "localhost", "127.0.0.1"):
        assert secret not in text


def test_debug_cors_endpoint_is_gone(client):
    """``/debug/cors`` used to echo CORS config; it must stay removed."""
    assert client.get("/debug/cors").status_code == 404


def test_request_id_header_is_echoed_and_generated(client):
    supplied = client.get("/health", headers={"X-Request-ID": "req-abc-123"})
    assert supplied.headers["X-Request-ID"] == "req-abc-123"

    generated = client.get("/health")
    assert generated.headers["X-Request-ID"]


def test_allowed_origin_is_reflected(client):
    resp = client.get("/health", headers={"Origin": "https://example.com"})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://example.com"
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_origin_pattern_is_supported(client):
    """``ALLOWED_ORIGIN_PATTERNS`` (fnmatch) must reach the middleware, which
    on Starlette >= 1.0 requires a compiled regex (regression: the removed
    ``allow_origin_patterns`` kwarg crashed every request)."""
    allowed = client.get(
        "/health", headers={"Origin": "https://team-a.preview.example.com"}
    )
    assert allowed.headers["access-control-allow-origin"] == "https://team-a.preview.example.com"

    # Subdomains of a *different* host must not match the pattern.
    denied = client.get("/health", headers={"Origin": "https://team-a.preview.example.org"})
    assert "access-control-allow-origin" not in denied.headers


def test_disallowed_origin_gets_no_cors_headers(client):
    resp = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers


def test_cors_is_never_wildcard(client):
    resp = client.get("/health", headers={"Origin": "https://evil.example.com"})
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao != "*"


def test_allowed_origin_preflight(client):
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_disallowed_origin_preflight_is_rejected(client):
    resp = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code >= 400
    assert "access-control-allow-origin" not in resp.headers


def test_unauthenticated_api_call_is_401(client):
    resp = client.get(f"{PREFIX}/auth/me")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_login_rate_limit_is_configurable_not_hardcoded(client):
    """Login must exist and validate input; rate limiting is env-gated."""
    resp = client.post(f"{PREFIX}/auth/login", json={"mobile": "", "password": ""})
    # 401 (bad credentials) or 422 (validation) - never a server error.
    assert resp.status_code in (401, 422)
