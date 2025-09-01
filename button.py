"""Button entities for The Masjid App integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MasjidDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button entities from a config entry."""
    coordinator: MasjidDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Create button entities
    button_entities = [
        ForceRefreshButton(coordinator),
        TestAzanButton(coordinator, entry),
    ]

    async_add_entities(button_entities)


class ForceRefreshButton(ButtonEntity):
    """Button entity to force refresh data from the server."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: MasjidDataCoordinator) -> None:
        """Initialize the force refresh button."""
        self.coordinator = coordinator

        # Set entity attributes
        prefix = coordinator.get_sanitized_mosque_prefix()
        self._attr_unique_id = f"{prefix}_force_refresh"
        self._attr_name = "Force Refresh"
        self._attr_translation_key = "force_refresh"
        self._attr_device_info = coordinator.get_device_info()

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Force refresh button pressed, requesting data update")
        await self.coordinator.async_request_refresh()


class TestAzanButton(ButtonEntity):
    """Button entity to test azan playback with test volume."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:play-circle"

    def __init__(self, coordinator: MasjidDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the test azan button."""
        self.coordinator = coordinator
        self._entry = entry

        # Set entity attributes
        prefix = coordinator.get_sanitized_mosque_prefix()
        self._attr_unique_id = f"{prefix}_test_azan"
        self._attr_name = "Test Azan"
        self._attr_translation_key = "test_azan"
        self._attr_device_info = coordinator.get_device_info()

    async def async_press(self) -> None:
        """Handle the button press - execute test azan."""
        _LOGGER.info("Test azan button pressed, executing test azan")

        # Get the scheduler and call the actual azan handler with "test" prayer type
        scheduler = self.hass.data[DOMAIN][self._entry.entry_id]["scheduler"]
        await scheduler._handle_azan("test")
