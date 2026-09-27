"""Runtime health and storage measurement for the Super Admin dashboard.

The dashboard used to return the literals ``system_health="Healthy"`` and
``storage_usage="45%"``. Nothing measured either value.

This module derives both from things that actually exist:

* ``system_health``  - a live ``SELECT 1`` round trip against the application
  database, plus a filesystem writability check on the configured upload
  directory. It reports ``Healthy`` only when both pass, ``Degraded`` when one
  fails, and ``Unavailable`` when the database is unreachable.
* ``storage_usage``  - the real on-disk size of the configured media/upload
  directory, reported as bytes/files. A percentage is deliberately **not**
  invented, because the application defines no storage quota, so there is no
  denominator to compute one against.
"""

import os
import shutil
import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def _media_dir() -> str:
    """The directory mounted at /media and used for uploads."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media"))


def _dir_usage(path: str) -> tuple:
    """Return (total_bytes, file_count) for a directory tree."""
    total = 0
    count = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
                count += 1
            except OSError:
                # A file removed mid-walk is not an error worth failing on.
                continue
    return total, count


def _human_bytes(n: int) -> str:
    step = 1024.0
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < step or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= step
    return f"{value:.1f} TB"


def check_system_health(db: Optional[Session]) -> tuple:
    """Return (status, latency_ms, detail).

    status is one of "Healthy", "Degraded", "Unavailable".
    """
    if db is None:
        return "Unavailable", None, "No database session available."

    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        return "Unavailable", None, f"Database unreachable: {type(exc).__name__}"

    problems = []
    if latency_ms > 1000:
        problems.append(f"slow database response ({latency_ms} ms)")

    media = _media_dir()
    try:
        os.makedirs(media, exist_ok=True)
        if not os.access(media, os.W_OK):
            problems.append("media directory is not writable")
    except OSError as exc:
        problems.append(f"media directory unavailable: {exc.strerror or exc}")

    if problems:
        return "Degraded", latency_ms, "; ".join(problems)
    return "Healthy", latency_ms, "Database reachable and media directory writable."


def measure_storage() -> dict:
    """Real usage of the media/upload directory plus the host filesystem it sits on."""
    media = _media_dir()
    try:
        os.makedirs(media, exist_ok=True)
        used_bytes, file_count = _dir_usage(media)
        media_available = True
    except OSError:
        used_bytes, file_count, media_available = 0, 0, False

    disk = None
    try:
        usage = shutil.disk_usage(media if media_available else os.path.abspath(os.sep))
        disk = {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            # This one is a real percentage: `shutil.disk_usage` reports the
            # filesystem's actual capacity, so the ratio is meaningful.
            "percent_used": round((usage.used / usage.total) * 100, 1) if usage.total else None,
        }
    except OSError:
        disk = None

    return {
        "media_path": media,
        "media_available": media_available,
        "used_bytes": used_bytes,
        "file_count": file_count,
        "used_human": _human_bytes(used_bytes),
        "disk": disk,
        # Short label for the dashboard card. Real measurement, not a guess.
        "label": f"{_human_bytes(used_bytes)} in {file_count} file{'s' if file_count != 1 else ''}",
    }
