"""CT (America/Chicago) formatting without tzdata. US DST rule (2nd Sun Mar .. 1st Sun Nov, 2am local)."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

def _nth_sunday(year: int, month: int, n: int) -> datetime:
    d = datetime(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)

def to_ct(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    u = dt.astimezone(timezone.utc).replace(tzinfo=None)
    start = _nth_sunday(u.year, 3, 2) + timedelta(hours=8)   # 2am CST = 08Z
    end = _nth_sunday(u.year, 11, 1) + timedelta(hours=7)    # 2am CDT = 07Z
    dst = start <= u < end
    off = -5 if dst else -6
    return (u + timedelta(hours=off)).replace(tzinfo=timezone(timedelta(hours=off), "CDT" if dst else "CST"))

def fmt(dt: datetime | None, with_date: bool = True) -> str:
    if dt is None:
        return "unknown"
    c = to_ct(dt)
    return c.strftime(("%Y-%m-%d " if with_date else "") + "%H:%M") + " CT"

def parse_zulu(s: str) -> datetime | None:
    try:
        return datetime.strptime((s or "").strip()[:20], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None
