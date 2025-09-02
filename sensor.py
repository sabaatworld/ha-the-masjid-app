"""Sensor entities for diagnostic information and prayer times."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, PRAYERS
from .coordinator import MasjidDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    # This is called when the integration is set up via YAML
    # We don't support this, so we'll just return
    return


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities from a config entry."""
    coordinator: MasjidDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Create diagnostic sensor entities
    sensor_entities = [
        LastFetchTimeSensor(coordinator),
        LastCacheTimeSensor(coordinator),
    ]

    # Add prayer time sensor entities
    for prayer in PRAYERS:
        if prayer != "test":
            sensor_entities.append(
                PrayerTimeSensor(
                    coordinator=coordinator,
                    prayer=prayer,
                    entity_type="azan"
                )
            )

    # Add iqama time sensor entities
    for prayer in PRAYERS:
        if prayer != "test":
            sensor_entities.append(
                PrayerTimeSensor(
                    coordinator=coordinator,
                    prayer=prayer,
                    entity_type="iqama"
                )
            )

    async_add_entities(sensor_entities)


class LastFetchTimeSensor(SensorEntity):
    """Representation of the last successful fetch time sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MasjidDataCoordinator) -> None:
        """Initialize the last fetch time sensor."""
        self.coordinator = coordinator

        # Set entity attributes
        prefix = coordinator.get_sanitized_mosque_prefix()
        self._attr_unique_id = f"{prefix}_last_fetch_time"
        self._attr_translation_key = "last_fetch_time"
        self._attr_translation_placeholders = {}
        self._attr_device_info = coordinator.get_device_info()

    @property
    def native_value(self) -> datetime | None:
        """Return the last successful fetch time."""
        return self.coordinator.last_successful_fetch

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class LastCacheTimeSensor(SensorEntity):
    """Representation of the last successful cache time sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MasjidDataCoordinator) -> None:
        """Initialize the last cache time sensor."""
        self.coordinator = coordinator

        # Set entity attributes
        prefix = coordinator.get_sanitized_mosque_prefix()
        self._attr_unique_id = f"{prefix}_last_cache_time"
        self._attr_translation_key = "last_cache_time"
        self._attr_translation_placeholders = {}
        self._attr_device_info = coordinator.get_device_info()

    @property
    def native_value(self) -> datetime | None:
        """Return the last successful cache time."""
        return self.coordinator.last_successful_cache

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class PrayerTimeSensor(SensorEntity):
    """Representation of a prayer time sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:clock"

    def __init__(
        self,
        coordinator: MasjidDataCoordinator,
        prayer: str,
        entity_type: str,
    ) -> None:
        """Initialize the prayer time sensor."""
        self.coordinator = coordinator
        self._prayer = prayer
        self._entity_type = entity_type

        # Set entity attributes
        prefix = coordinator.get_sanitized_mosque_prefix()
        self._attr_unique_id = f"{prefix}_{prayer}_{entity_type}"
        self._attr_name = f"{prayer.title()} {entity_type.title()}"
        self._attr_translation_key = "prayer_time"
        self._attr_translation_placeholders = {
            "prayer": prayer.title(),
            "type": entity_type.title()
        }
        self._attr_device_info = coordinator.get_device_info()

    @property
    def native_value(self) -> str | None:
        """Return the time value as a string."""
        if self._entity_type == "azan":
            prayer_times = self.coordinator.get_prayer_times()
            if not prayer_times:
                return None

            time_str = prayer_times.get(self._prayer)
        else:  # iqama
            iqama_times = self.coordinator.get_iqama_times()
            if not iqama_times:
                return None

            time_str = iqama_times.get(self._prayer)

        return time_str

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
