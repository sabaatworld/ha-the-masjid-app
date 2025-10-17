from __future__ import annotations

import logging
import re
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)


class MasjidEntityRegistry:
    """Registry for entities in The Masjid App integration."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._entities: dict[str, Entity] = {}

    def register_entity(self, key: str, entity: Entity) -> None:
        """Register an entity."""
        self._entities[key] = entity
        _LOGGER.debug("Registered entity with key: %s", key)

    def get_entity(self, key: str) -> Entity | None:
        """Get an entity from the registry."""
        return self._entities.get(key)


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
