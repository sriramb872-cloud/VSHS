"""Ad-hoc API smoke test for the newly added endpoints (QA only)."""
import json
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "http://localhost:8000/api/v1"


class Res:
    def __init__(self, status, body):
        self.status_code = status
        self.text = body

    def json(self):
        return json.loads(self.text)


def call(method, path, token=None, params=None, json_body=None):
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    data = None
    headers = {}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            return Res(r.status, r.read().decode())
    except HTTPError as e:
        return Res(e.code, e.read().decode())


def login(mobile, password):
    # POST /auth/login is rate limited to 5/minute, so back off and retry.
    for attempt in range(6):
        r = call("POST", "/auth/login", json_body={"mobile": mobile, "password": password})
        if r.status_code == 200:
            return r.json()["access_token"]
        if r.status_code in (429, 401) and attempt < 5:
            time.sleep(12)
            continue
        raise SystemExit(f"login failed for {mobile}: {r.status_code} {r.text}")
    raise SystemExit(f"login gave up for {mobile}")


def show(label, r):
    print(f"\n--- {label}: HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2)[:1800])
    except Exception:
        print(r.text[:1800])


def main():
    sa = login("8019302351", "super")
    pr = login("9000000001", "QaTest#2026p")
    pr_b = login("9000000009", "QaTestB#2026")
    st = login("9000001001", "QaStu#2026")

    show("GET /roles (super admin)", call("GET", "/roles", sa))
    show("GET /roles (principal -> must be 403)", call("GET", "/roles", pr))

    show("GET /reports/platform (super admin)", call("GET", "/reports/platform", sa))
    show(
        "GET /reports/platform (principal -> must be 403)",
        call("GET", "/reports/platform", pr),
    )

    show(
        "GET /dashboard/super-admin (real health/storage)",
        call("GET", "/dashboard/super-admin", sa),
    )

    show(
        "GET /search?q=Qa (super admin, was always empty)",
        call("GET", "/search", sa, params={"q": "Qa"}),
    )
    show(
        "GET /search?q=Qa (principal, own school)",
        call("GET", "/search", pr, params={"q": "Qa"}),
    )
    show(
        "GET /search?q=Qa (principal of school 7, cross-tenant check)",
        call("GET", "/search", pr_b, params={"q": "Qa"}),
    )
    show(
        "GET /search?q=Qa (student, self only)",
        call("GET", "/search", st, params={"q": "Qa"}),
    )

    show(
        "GET /attendance/reports/summary (principal, 2026)",
        call(
            "GET",
            "/attendance/reports/summary",
            pr,
            params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
        ),
    )
    show(
        "GET /attendance/reports/summary (bad range -> 400)",
        call(
            "GET",
            "/attendance/reports/summary",
            pr,
            params={"start_date": "2026-12-31", "end_date": "2026-01-01"},
        ),
    )
    show(
        "GET /attendance/reports/summary (student -> 403)",
        call(
            "GET",
            "/attendance/reports/summary",
            st,
            params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
        ),
    )

    show("GET /files/metadata/1 (missing -> 404)", call("GET", "/files/metadata/1", sa))
    show("GET /files/metadata (list)", call("GET", "/files/metadata", sa))


if __name__ == "__main__":
    sys.exit(main())
