"""Button entities for The Masjid App integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_KEY_FORCE_REFRESH,
    ENTITY_KEY_TEST_AZAN,
    ENTITY_KEY_TEST_AZAN_SCHEDULE,
    ENTITY_KEY_TEST_PRAYER_SCHEDULE,
    ENTITY_KEY_CAR_START_MINUTES,
    ENTITY_KEY_WATER_RECIRC_MINUTES,
    ENTITY_KEY_RAMADAN_REMINDER_MINUTES,
    CAR_START_MINUTES_DEFAULT,
    WATER_RECIRC_MINUTES_DEFAULT,
    RAMADAN_REMINDER_MINUTES_DEFAULT,
)
from .coordinator import MasjidDataCoordinator
from .helpers import MasjidEntityRegistry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button entities from a config entry."""
    coordinator: MasjidDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_registry: MasjidEntityRegistry = hass.data[DOMAIN][entry.entry_id]["entity_registry"]

    # Create button entities
    button_entities = []
    force_refresh_entity = ForceRefreshButton(coordinator)
    button_entities.append(force_refresh_entity)
    entity_registry.register_entity(ENTITY_KEY_FORCE_REFRESH, force_refresh_entity)

    test_azan_entity = TestAzanButton(coordinator, entry)
    button_entities.append(test_azan_entity)
    entity_registry.register_entity(ENTITY_KEY_TEST_AZAN, test_azan_entity)

    test_azan_schedule_entity = TestAzanScheduleButton(coordinator, entry)
    button_entities.append(test_azan_schedule_entity)
    entity_registry.register_entity(ENTITY_KEY_TEST_AZAN_SCHEDULE, test_azan_schedule_entity)

    test_prayer_schedule_entity = TestPrayerScheduleButton(coordinator, entry)
    button_entities.append(test_prayer_schedule_entity)
    entity_registry.register_entity(ENTITY_KEY_TEST_PRAYER_SCHEDULE, test_prayer_schedule_entity)

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
        prefix = coordinator.get_effective_mosque_name()
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
        prefix = coordinator.get_effective_mosque_name()
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


class TestAzanScheduleButton(ButtonEntity):
    """Button entity to test the MasjidScheduler's schedule_from_data method."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: MasjidDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the test azan schedule button."""
        self.coordinator = coordinator
        self._entry = entry

        # Set entity attributes
        prefix = coordinator.get_effective_mosque_name()
        self._attr_unique_id = f"{prefix}_test_azan_schedule"
        self._attr_name = "Test Azan Schedule"
        self._attr_translation_key = "test_azan_schedule"
        self._attr_device_info = coordinator.get_device_info()

    async def async_press(self) -> None:
        """Handle the button press - test the scheduler with test data."""
        _LOGGER.info("Test azan schedule button pressed, testing scheduler with test data")

        # Get the scheduler
        scheduler = self.hass.data[DOMAIN][self._entry.entry_id]["scheduler"]

        # Get current data from coordinator
        current_data = self.coordinator.data or {}

        # Create test data by copying current data and adding test azan entry
        test_data = current_data.copy()

        # Ensure masjid structure exists
        if "masjid" not in test_data:
            test_data["masjid"] = {}

        # Ensure azan structure exists
        if "azan" not in test_data["masjid"]:
            test_data["masjid"]["azan"] = {}

        # Calculate time for next minute
        now = datetime.now()
        next_minute = now + timedelta(minutes=1)
        test_time_str = next_minute.strftime("%I:%M %p")

        # Add test azan entry for next minute
        test_data["masjid"]["azan"]["test"] = test_time_str

        _LOGGER.info("Created test data with test azan scheduled for %s", test_time_str)
        _LOGGER.debug("Test data structure: %s", test_data)

        # Call schedule_from_data with test data
        scheduler.schedule_from_data(test_data)

        _LOGGER.info("Test azan schedule completed - test azan should trigger in approximately 1 minute")


class TestPrayerScheduleButton(ButtonEntity):
    """Button entity to test prayer time scheduling for practical actions."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: MasjidDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the test prayer schedule button."""
        self.coordinator = coordinator
        self._entry = entry

        # Set entity attributes
        prefix = coordinator.get_effective_mosque_name()
        self._attr_unique_id = f"{prefix}_test_prayer_schedule"
        self._attr_name = "Test Prayer Schedule"
        self._attr_translation_key = "test_prayer_schedule"
        self._attr_device_info = coordinator.get_device_info()

    async def async_press(self) -> None:
        """Handle the button press - test prayer time scheduling for practical actions."""
        _LOGGER.info("Test prayer schedule button pressed, testing prayer time scheduling")

        # Get the scheduler
        scheduler = self.hass.data[DOMAIN][self._entry.entry_id]["scheduler"]

        # Get current data from coordinator
        current_data = self.coordinator.data or {}

        # Create test data by copying current data
        test_data = current_data.copy()

        # Ensure masjid structure exists
        if "masjid" not in test_data:
            test_data["masjid"] = {}

        # Get current offset values from number entities
        entity_registry: MasjidEntityRegistry = self.hass.data[DOMAIN][self._entry.entry_id]["entity_registry"]
        car_mins_entity = entity_registry.get_entity(ENTITY_KEY_CAR_START_MINUTES)
        car_mins = max(0, int(car_mins_entity.native_value if car_mins_entity else CAR_START_MINUTES_DEFAULT))

        water_mins_entity = entity_registry.get_entity(ENTITY_KEY_WATER_RECIRC_MINUTES)
        water_mins = max(0, int(water_mins_entity.native_value if water_mins_entity else WATER_RECIRC_MINUTES_DEFAULT))

        ramadan_mins_entity = entity_registry.get_entity(ENTITY_KEY_RAMADAN_REMINDER_MINUTES)
        ramadan_mins = max(0, int(ramadan_mins_entity.native_value if ramadan_mins_entity else RAMADAN_REMINDER_MINUTES_DEFAULT))

        # Find the largest offset
        largest_offset = max(car_mins, water_mins, ramadan_mins)

        _LOGGER.info("Offset values - Car: %d min, Water: %d min, Ramadan: %d min, Largest: %d min",
                    car_mins, water_mins, ramadan_mins, largest_offset)

        # Calculate test prayer time: now + largest_offset + 1 minute
        # This ensures the largest offset action triggers in 1 minute
        now = datetime.now()
        test_prayer_time = now + timedelta(minutes=largest_offset + 1)
        test_time_str = test_prayer_time.strftime("%I:%M %p")

        # Add test prayer time entry (not azan time)
        # The scheduler expects prayer times in masjid[prayer] format
        test_data["masjid"]["test"] = test_time_str

        _LOGGER.info("Created test data with test prayer time scheduled for %s (largest offset action will trigger in 1 minute)",
                    test_time_str)
        _LOGGER.debug("Test data structure: %s", test_data)

        # Call schedule_from_data with test data
        scheduler.schedule_from_data(test_data)

        _LOGGER.info("Test prayer schedule completed - largest offset action should trigger in approximately 1 minute")
