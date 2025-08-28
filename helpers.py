from __future__ import annotations

import re
from datetime import datetime, time, timedelta


def safe_slug(base: str) -> str:
    slug = base.lower().strip()
    slug = re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "masjid"


def parse_prayer_time(text_time: str) -> datetime:
    up = text_time.upper()
    if " " not in up:
        up = up.replace("AM", " AM").replace("PM", " PM")
    return datetime.strptime(up, "%I:%M %p")


def minus_minutes(dt: datetime, minutes: int) -> time:
    return (dt - timedelta(minutes=minutes)).time()


