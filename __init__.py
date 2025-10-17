from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_REFRESH_INTERVAL_HOURS, CONF_MASJID_ID, CONF_REFRESH_INTERVAL_HOURS
from .coordinator import MasjidDataCoordinator
from .scheduler import MasjidScheduler
from .helpers import MasjidEntityRegistry

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    refresh_hours = entry.options.get(CONF_REFRESH_INTERVAL_HOURS, DEFAULT_REFRESH_INTERVAL_HOURS)
    masjid_id = entry.options.get(CONF_MASJID_ID)
    coordinator = MasjidDataCoordinator(
        hass,
        masjid_id=masjid_id,
        update_interval=timedelta(hours=refresh_hours),
        config_entry=entry,
    )

    entity_registry = MasjidEntityRegistry()
    scheduler = MasjidScheduler(hass, entry.options, coordinator, entity_registry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "scheduler": scheduler,
        "entity_registry": entity_registry,
    }

    await coordinator.async_config_entry_first_refresh()
    if coordinator.data:
        scheduler.schedule_from_data(coordinator.data)

    def _on_update() -> None:
        if coordinator.data:
            scheduler.schedule_from_data(coordinator.data)

    entry.async_on_unload(coordinator.async_add_listener(_on_update))
    await hass.config_entries.async_forward_entry_setups(entry, ["number", "switch", "sensor", "button"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Masjid App integration")

    # Retrieve the scheduler instance
    masjid_data = hass.data[DOMAIN].get(entry.entry_id)
    if masjid_data and "scheduler" in masjid_data:
        scheduler = masjid_data["scheduler"]
        _LOGGER.debug("Clearing all scheduled callbacks")
        scheduler.clear_schedules()
    else:
        _LOGGER.error("Scheduler not found during unload, cannot clear callbacks.")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["number", "switch", "sensor", "button"]
    )

    # Clean up hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("Masjid App integration unloaded successfully")
    else:
        _LOGGER.error("Failed to unload one or more platforms")

    return unload_ok
