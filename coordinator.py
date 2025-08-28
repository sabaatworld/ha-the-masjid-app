from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import timedelta, datetime
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_DEVICE_ID, CONF_MASJID_NAME

_LOGGER = logging.getLogger(__name__)


class MasjidDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, masjid_id: int, update_interval: timedelta, config_entry):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_data",
            update_interval=update_interval,
        )
        self._masjid_id = masjid_id
        self._config_entry = config_entry
        self._cached: dict[str, Any] | None = None
        self._last_successful_fetch: datetime | None = None
        self._last_successful_cache: datetime | None = None

    @property
    def last_successful_fetch(self) -> datetime | None:
        """Return the last successful fetch time."""
        return self._last_successful_fetch

    @property
    def last_successful_cache(self) -> datetime | None:
        """Return the last successful cache time."""
        return self._last_successful_cache

    def get_prayer_times(self) -> dict[str, str] | None:
        """Get prayer times from the current data."""
        if not self.data or "masjid" not in self.data:
            return None

        azan_data = self.data["masjid"].get("azan")
        if not azan_data:
            return None

        prayer_times = {
            "fajr": azan_data.get("fajr"),
            "sunrise": azan_data.get("sunrise"),
            "dhuhr": azan_data.get("zuhr"),  # API uses "zuhr" but we want "dhuhr"
            "asr": azan_data.get("asr"),
            "maghrib": azan_data.get("maghrib"),
            "isha": azan_data.get("isha"),
            "qiyam": azan_data.get("qiyam"),
        }

        # Filter out None values and return only available prayer times
        return {k: v for k, v in prayer_times.items() if v is not None}

    def get_iqama_times(self) -> dict[str, str] | None:
        """Get iqama times from the current data."""
        if not self.data or "masjid" not in self.data:
            return None

        masjid_data = self.data["masjid"]

        # Get iqama times from direct prayer fields (like the original ab demon script)
        iqama_times = {
            "fajr": masjid_data.get("fajr"),
            "sunrise": None,  # Not typically used for iqama
            "dhuhr": masjid_data.get("zuhr"),  # API uses "zuhr" but we want "dhuhr"
            "asr": masjid_data.get("asr"),
            "maghrib": masjid_data.get("maghrib"),
            "isha": masjid_data.get("isha"),
            "qiyam": None,  # Not typically used for iqama
        }

        # Filter out None values and return only available prayer times
        return {k: v for k, v in iqama_times.items() if v is not None}

    def get_mosque_name(self) -> str | None:
        """Get the mosque name from the current data."""
        if not self.data or "masjid" not in self.data:
            return None

        return self.data["masjid"].get("name")

    def get_effective_mosque_name(self) -> str:
        """Get the effective mosque name from persisted data or server data."""
        # First try persisted name from config entry
        persisted_name = self._config_entry.data.get(CONF_MASJID_NAME)
        if persisted_name:
            return persisted_name

        # Fallback to server-fetched name
        server_name = self.get_mosque_name()
        if server_name:
            return server_name

        # Final fallback if no data yet
        return "Masjid"

    def get_sanitized_mosque_prefix(self) -> str:
        """Get sanitized mosque name for use as entity ID prefix."""
        from .helpers import safe_slug
        name = self.get_effective_mosque_name()
        return safe_slug(name)

    def get_masjid_id(self) -> int:
        """Get the masjid ID from the config entry."""
        return self._masjid_id

    def get_device_info(self) -> dict[str, Any]:
        """Get device info for all entities in this integration."""
        return {
            "identifiers": {(DOMAIN, self.get_device_id())},
            "name": self.get_effective_mosque_name(),
            "manufacturer": "The Masjid App",
            "model": f"Masjid ID: {self.get_masjid_id()}",
        }

    def ensure_masjid_name_persisted(self) -> None:
        """Ensure the masjid name is persisted in config entry data (migration helper)."""
        # If we don't have a persisted name but we have server data, save it
        if not self._config_entry.data.get(CONF_MASJID_NAME) and self.data and "masjid" in self.data:
            server_name = self.data["masjid"].get("name")
            if server_name:
                data = dict(self._config_entry.data)
                data[CONF_MASJID_NAME] = server_name
                self.hass.config_entries.async_update_entry(self._config_entry, data=data)
                _LOGGER.info("Persisted masjid name for migration: %s", server_name)

    def get_device_id(self) -> str:
        """Get the persistent device ID from the config entry data."""
        device_id = self._config_entry.data.get(CONF_DEVICE_ID)

        # If no device ID exists (migration case), generate one and store it
        if not device_id:
            device_id = str(uuid.uuid4())
            data = dict(self._config_entry.data)
            data[CONF_DEVICE_ID] = device_id
            self.hass.config_entries.async_update_entry(self._config_entry, data=data)
            _LOGGER.info("Generated new device ID for migration: %s", device_id)

        return device_id

    async def _async_update_data(self) -> dict[str, Any]:
        url = f"http://themasjidapp.net/{self._masjid_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status}")
                    data: dict[str, Any] = await resp.json()
        except Exception as err:  # noqa: BLE001
            if self._cached is not None:
                _LOGGER.warning("Fetch failed (%s); using cached response", err)
                return self._cached
            raise UpdateFailed(err) from err

        # Update timestamps
        self._last_successful_fetch = dt_util.utcnow()

        # Cache and return
        self._cached = data
        self._last_successful_cache = dt_util.utcnow()

        # Ensure masjid name is persisted for existing installations
        self.ensure_masjid_name_persisted()

        return data


