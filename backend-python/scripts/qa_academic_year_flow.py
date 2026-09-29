# backend-python/scripts/qa_academic_year_flow.py
"""
End-to-end verification of the Academic Year flow against a RUNNING backend.

Covers the 8 required scenarios plus validation and cross-school isolation:

  S1  Super Admin creates a school with NO academic year
  S2  Principal of that school gets a usable (not broken) empty state
  S3  Principal creates 2026-2027 as Active -> exactly one ACTIVE
  S4  Principal creates 2027-2028 inactive   -> 2026-2027 stays ACTIVE
  S5  Principal activates 2027-2028          -> previous year auto-closes
  S6  Principal can list every year of the school
  S7  Viewing another year never changes the ACTIVE year
  S8  Two schools keep independent, isolated academic year sets

Run the API first:
    python -m uvicorn main:app --host 127.0.0.1 --port 8000

Usage:
    python scripts/qa_academic_year_flow.py
"""
import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app.core.database import engine  # noqa: E402

BASE = "http://localhost:8000/api/v1"
YEAR_HEADER = "X-Academic-Year-Id"

_results = []


class Res:
    def __init__(self, status, body):
        self.status_code = status
        self.text = body

    def json(self):
        return json.loads(self.text)

    def detail(self):
        try:
            d = self.json().get("detail")
            if isinstance(d, list) and d:
                return d[0].get("msg", str(d[0]))
            return d
        except Exception:  # noqa: BLE001
            return self.text[:200]


def call(method, path, token=None, params=None, json_body=None, headers=None):
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    data = None
    hdrs = {"Content-Type": "application/json"} if json_body is not None else {}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers:
        hdrs.update({k: v for k, v in headers.items() if v is not None})
    req = Request(url, data=data if json_body is None else json.dumps(json_body).encode(),
                  headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            return Res(r.status, r.read().decode())
    except HTTPError as e:
        return Res(e.code, e.read().decode())


def login(mobile, password):
    # POST /auth/login is rate limited to 5/minute, so back off and retry.
    for attempt in range(8):
        r = call("POST", "/auth/login", json_body={"mobile": mobile, "password": password})
        if r.status_code == 200:
            return r.json()["access_token"]
        if r.status_code == 429 and attempt < 7:
            time.sleep(13)
            continue
        raise SystemExit(f"login failed for {mobile}: {r.status_code} {r.text}")
    raise SystemExit("login gave up")


def check(label, ok, info=""):
    _results.append((label, bool(ok), info))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" -> {info}" if info else ""))


def db_scalar(sql, **params):
    """Execute a statement and return the first column of the first row."""
    with engine.begin() as conn:
        return conn.execute(text(sql), params).scalar()


def db_rows(sql, **params):
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql), params)]


def cleanup_verification_rows():
    """Remove only the rows this script creates (schools named 'AY Flow School...')."""
    with engine.begin() as conn:
        ids = [
            r[0]
            for r in conn.execute(
                text("SELECT school_id FROM schools WHERE school_name LIKE 'AY Flow School%'")
            )
        ]
        if not ids:
            print("  nothing to clean up")
            return
        placeholders = ",".join(f":s{i}" for i in range(len(ids)))
        params = {f"s{i}": v for i, v in enumerate(ids)}
        # users first (schools.school_id is ON DELETE SET NULL); everything
        # else - academic_years, school_settings, principal_profiles,
        # audit_logs - cascades off the school row.
        conn.execute(text(f"DELETE FROM users WHERE school_id IN ({placeholders})"), params)
        conn.execute(text(f"DELETE FROM schools WHERE school_id IN ({placeholders})"), params)
    print(f"  removed verification schools: {ids}")


def active_years(school_id):
    return db_rows(
        "SELECT academic_year_id, year_name, status, is_current "
        "FROM academic_years WHERE school_id = :sid AND status = 'ACTIVE'",
        sid=school_id,
    )


def year_rows(school_id):
    return db_rows(
        "SELECT academic_year_id, year_name, status, is_current "
        "FROM academic_years WHERE school_id = :sid ORDER BY start_date, academic_year_id",
        sid=school_id,
    )


def main():
    stamp = int(time.time()) % 1000000
    suffix = f"{stamp:06d}"

    print("=" * 78)
    print("ACADEMIC YEAR FLOW - END TO END VERIFICATION")
    print("=" * 78)

    # ------------------------------------------------------------------
    print("\nLogin: Super Admin")
    sa = login("8019302351", "super")

    # ------------------------------------------------------------------
    print("\nSCENARIO 1 - Super Admin creates a school with NO academic year")
    code_a = f"AYA{suffix}"
    r = call("POST", "/schools", token=sa, json_body={
        "name": f"AY Flow School A {suffix}",
        "code": code_a,
        "is_active": True,
    })
    check("S1 school A created", r.status_code == 201, f"HTTP {r.status_code}")
    if r.status_code != 201:
        raise SystemExit("cannot continue: school A creation failed")
    school_a = r.json()["id"]

    code_b = f"AYB{suffix}"
    r = call("POST", "/schools", token=sa, json_body={
        "name": f"AY Flow School B {suffix}",
        "code": code_b,
    })
    check("S1 school B created", r.status_code == 201, f"HTTP {r.status_code}")
    if r.status_code != 201:
        raise SystemExit("cannot continue: school B creation failed")
    school_b = r.json()["id"]

    n_a = db_scalar("SELECT COUNT(*) FROM academic_years WHERE school_id = :s", s=school_a)
    n_b = db_scalar("SELECT COUNT(*) FROM academic_years WHERE school_id = :s", s=school_b)
    check("S1 school A has ZERO academic years", n_a == 0, f"count={n_a}")
    check("S1 school B has ZERO academic years", n_b == 0, f"count={n_b}")

    # ------------------------------------------------------------------
    print("\n  Creating a Principal for each school (Super Admin only flow)")
    mobile_a = f"9111{suffix}"
    mobile_b = f"9222{suffix}"
    password = "AyVerify#2026"
    for sid, mob, nm in ((school_a, mobile_a, "AY Principal A"),
                         (school_b, mobile_b, "AY Principal B")):
        r = call("POST", "/principals", token=sa, json_body={
            "school_id": sid, "full_name": nm, "mobile": mob, "password": password,
        })
        check(f"principal {nm} created for school {sid}", r.status_code == 201,
              f"HTTP {r.status_code} {r.detail() if r.status_code != 201 else ''}")
        if r.status_code != 201:
            raise SystemExit("cannot continue: principal creation failed")

    pa = login(mobile_a, password)
    pb = login(mobile_b, password)

    # ------------------------------------------------------------------
    print("\nSCENARIO 2 - Principal sees an empty (not broken) year list")
    r = call("GET", "/academic-years", token=pa)
    check("S2 GET /academic-years returns 200", r.status_code == 200, f"HTTP {r.status_code}")
    check("S2 list is empty (no years yet)",
          r.status_code == 200 and r.json() == [], f"body={r.text[:120]}")

    r = call("GET", "/academic-years/active", token=pa)
    check("S2 GET /academic-years/active degrades gracefully (404 + clear detail)",
          r.status_code == 404 and "No academic year" in str(r.detail()),
          f"HTTP {r.status_code} {r.detail()}")

    r = call("GET", "/announcements/", token=pa)
    check("S2 year-scoped screen does NOT crash with zero years",
          r.status_code == 200, f"HTTP {r.status_code} {r.text[:120]}")

    # ------------------------------------------------------------------
    print("\nSCENARIO 3 - Create 2026-2027 with Active = YES")
    r = call("POST", "/academic-years", token=pa, json_body={
        "name": "2026-2027", "start_date": "2026-06-01",
        "end_date": "2027-05-31", "is_active": True,
    })
    check("S3 2026-2027 created", r.status_code == 201, f"HTTP {r.status_code} {r.detail() if r.status_code != 201 else ''}")
    if r.status_code != 201:
        raise SystemExit("cannot continue: S3 creation failed")
    y1 = r.json()
    check("S3 2026-2027 is ACTIVE", y1.get("status") == "ACTIVE" and y1.get("is_active") is True,
          f"status={y1.get('status')} is_active={y1.get('is_active')}")
    act = active_years(school_a)
    check("S3 exactly ONE active year for school A", len(act) == 1, f"active={act}")
    check("S3 active year is 2026-2027", act and act[0][1] == "2026-2027", f"active={act}")

    # ------------------------------------------------------------------
    print("\nSCENARIO 4 - Create 2027-2028 with Active = NO")
    r = call("POST", "/academic-years", token=pa, json_body={
        "name": "2027-2028", "start_date": "2027-06-01",
        "end_date": "2028-05-31", "is_active": False,
    })
    check("S4 2027-2028 created", r.status_code == 201, f"HTTP {r.status_code} {r.detail() if r.status_code != 201 else ''}")
    if r.status_code != 201:
        raise SystemExit("cannot continue: S4 creation failed")
    y2 = r.json()
    check("S4 2027-2028 is INACTIVE/UPCOMING", y2.get("status") == "UPCOMING" and y2.get("is_active") is False,
          f"status={y2.get('status')} is_active={y2.get('is_active')}")
    act = active_years(school_a)
    check("S4 2026-2027 REMAINS the active year", len(act) == 1 and act[0][1] == "2026-2027", f"active={act}")

    # ------------------------------------------------------------------
    print("\nSCENARIO 5 - Activate 2027-2028")
    r = call("POST", f"/academic-years/{y2['id']}/activate", token=pa)
    check("S5 activate 2027-2028 -> 200", r.status_code == 200, f"HTTP {r.status_code} {r.detail() if r.status_code != 200 else ''}")
    act = active_years(school_a)
    check("S5 exactly ONE active year (never two)", len(act) == 1, f"active={act}")
    check("S5 active year is now 2027-2028", act and act[0][1] == "2027-2028", f"active={act}")
    closed = db_rows(
        "SELECT year_name, status, is_current FROM academic_years "
        "WHERE school_id = :s AND year_name = '2026-2027'", s=school_a)
    check("S5 2026-2027 auto-deactivated", closed and closed[0][1] == "CLOSED" and closed[0][2] == 0,
          f"2026-2027 -> {closed}")

    # ------------------------------------------------------------------
    print("\nSCENARIO 6 - Principal can list every year of the school")
    r = call("GET", "/academic-years", token=pa)
    names = [y["name"] for y in r.json()] if r.status_code == 200 else []
    check("S6 2026-2027 visible", "2026-2027" in names, f"names={names}")
    check("S6 2027-2028 visible", "2027-2028" in names, f"names={names}")
    check("S6 both years returned in one list", len(names) >= 2, f"names={names}")

    # ------------------------------------------------------------------
    print("\nSCENARIO 7 - Viewing an older year does NOT change the Active year")
    r = call("GET", "/academic-years/active", token=pa)
    check("S7 default (no header) resolves ACTIVE year 2027-2028",
          r.status_code == 200 and r.json()["name"] == "2027-2028",
          f"HTTP {r.status_code} name={r.json().get('name') if r.status_code == 200 else r.text[:100]}")

    r = call("GET", "/academic-years/active", token=pa,
             headers={YEAR_HEADER: str(y1["id"])})
    check("S7 with X-Academic-Year-Id -> selected year 2026-2027 is returned",
          r.status_code == 200 and r.json()["name"] == "2026-2027",
          f"HTTP {r.status_code} name={r.json().get('name') if r.status_code == 200 else r.text[:100]}")

    r = call("GET", "/announcements/", token=pa, headers={YEAR_HEADER: str(y1["id"])})
    check("S7 year-scoped data call for 2026-2027 succeeds",
          r.status_code == 200, f"HTTP {r.status_code} {r.text[:120]}")

    r = call("GET", "/academic-years", token=pa)
    act = active_years(school_a)
    check("S7 Active year still 2027-2028 after viewing 2026-2027",
          len(act) == 1 and act[0][1] == "2027-2028", f"active={act}")

    # ------------------------------------------------------------------
    print("\nSCENARIO 8 - Two schools keep independent academic years")
    r = call("POST", "/academic-years", token=pb, json_body={
        "name": "2025-2026", "start_date": "2025-06-01",
        "end_date": "2026-05-31", "is_active": True,
    })
    check("S8 school B creates its own active year", r.status_code == 201,
          f"HTTP {r.status_code} {r.detail() if r.status_code != 201 else ''}")

    act_a = active_years(school_a)
    act_b = active_years(school_b)
    check("S8 school A active year untouched by school B", len(act_a) == 1 and act_a[0][1] == "2027-2028",
          f"A active={act_a}")
    check("S8 school B has its own single active year", len(act_b) == 1 and act_b[0][1] == "2025-2026",
          f"B active={act_b}")

    r = call("GET", "/academic-years", token=pb)
    b_names = [y["name"] for y in r.json()] if r.status_code == 200 else []
    check("S8 principal B sees ONLY school B years",
          "2025-2026" in b_names and "2027-2028" not in b_names, f"B sees={b_names}")

    r = call("GET", f"/academic-years/{y1['id']}", token=pb)
    check("S8 principal B cannot READ school A's year (403)", r.status_code == 403,
          f"HTTP {r.status_code}")
    r = call("POST", f"/academic-years/{y1['id']}/activate", token=pb)
    check("S8 principal B cannot ACTIVATE school A's year (403)", r.status_code == 403,
          f"HTTP {r.status_code}")

    # ------------------------------------------------------------------
    print("\nVALIDATION")
    r = call("POST", "/academic-years", token=pa, json_body={
        "name": "Bad Range", "start_date": "2030-06-01", "end_date": "2030-05-31",
    })
    check("end date before start date rejected", r.status_code in (400, 422),
          f"HTTP {r.status_code} {r.detail()}")

    r = call("POST", "/academic-years", token=pa, json_body={
        "name": "2027-2028", "start_date": "2031-06-01", "end_date": "2032-05-31",
    })
    check("duplicate year name rejected", r.status_code == 400 and "already exists" in str(r.detail()),
          f"HTTP {r.status_code} {r.detail()}")

    r = call("POST", "/academic-years", token=pa, json_body={
        "name": "Overlap Test", "start_date": "2027-01-01", "end_date": "2027-12-31",
    })
    check("overlapping year rejected", r.status_code == 400 and "overlap" in str(r.detail()).lower(),
          f"HTTP {r.status_code} {r.detail()}")

    r = call("POST", "/academic-years", token=pa, json_body={
        "name": "Missing Dates", "start_date": "2035-06-01",
    })
    check("missing end date rejected", r.status_code == 422, f"HTTP {r.status_code}")

    # ------------------------------------------------------------------
    print("\nCLEANUP (drop only the verification rows, FK-safe order)")
    try:
        cleanup_verification_rows()
    except Exception as exc:  # noqa: BLE001 - never mask the real results
        print(f"  cleanup skipped: {exc}")

    # ------------------------------------------------------------------
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print("\n" + "=" * 78)
    print(f"RESULT: {passed}/{total} checks passed")
    for label, ok, info in _results:
        if not ok:
            print(f"  FAILED: {label} -> {info}")
    print("=" * 78)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        # Remove leftovers from a previous (possibly failed) run.
        cleanup_verification_rows()
    else:
        main()
