from __future__ import annotations

import logging
import re
from datetime import datetime, time, timedelta

_LOGGER = logging.getLogger(__name__)


def safe_slug(base: str) -> str:
    slug = base.lower().strip()
    slug = re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "masjid"


def parse_prayer_time(text_time: str) -> datetime | None:
    """
    Parse prayer time string to datetime object.

    Args:
        text_time: Time string in format "HH:MM AM/PM" or "HH:MMAM/PM"

    Returns:
        datetime object if parsing successful, None if parsing failed
    """
    try:
        up = text_time.upper()
        if " " not in up:
            up = up.replace("AM", " AM").replace("PM", " PM")
        return datetime.strptime(up, "%I:%M %p")
    except (ValueError, AttributeError) as e:
        _LOGGER.error("Failed to parse prayer time '%s': %s", text_time, e)
        return None


def minus_minutes(dt: datetime, minutes: int) -> time:
    return (dt - timedelta(minutes=minutes)).time()


