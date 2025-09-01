from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE, UnitOfTime, EntityCategory

from .const import (
    DOMAIN,
    PRAYERS,
    VOLUME_MIN,
    VOLUME_MAX,
    VOLUME_STEPS,
    CAR_START_MINUTES_DEFAULT,
    WATER_RECIRC_MINUTES_DEFAULT,
    RAMADAN_REMINDER_MINUTES_DEFAULT,
    CAR_WATER_MINUTES_MIN,
    CAR_WATER_MINUTES_MAX,
    RAMADAN_REMINDER_MIN,
    RAMADAN_REMINDER_MAX,
    CONF_CAR_START_MINUTES,
    CONF_WATER_RECIRC_MINUTES,
    CONF_RAMADAN_REMINDER_MINUTES,
    CONF_AZAN_VOLUME_FAJR,
    CONF_AZAN_VOLUME_DHUHR,
    CONF_AZAN_VOLUME_ASR,
    CONF_AZAN_VOLUME_MAGHRIB,
    CONF_AZAN_VOLUME_ISHA,
    CONF_AZAN_VOLUME_TEST,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    # Get coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get sanitized prefix for entity IDs
    prefix = coordinator.get_sanitized_mosque_prefix()

    entities: list[NumberEntity] = []
    for p in PRAYERS:
        entities.append(AzanVolumeNumber(f"{p.title()} Azan Volume", f"{prefix}_{p}_azan_volume", entry, p, coordinator))

    entities.append(CarStartMinutesNumber("Car Start", f"{prefix}_car_start_minutes", entry, coordinator))
    entities.append(WaterRecircMinutesNumber("Water Recirculation", f"{prefix}_water_recirc_minutes", entry, coordinator))
    entities.append(RamadanReminderMinutesNumber("Ramadan Reminder", f"{prefix}_ramadan_reminder_minutes", entry, coordinator))

    # Add diagnostic test azan volume entity
    test_volume_entity = AzanVolumeNumber("Test Azan Volume", f"{prefix}_test_azan_volume", entry, "test", coordinator)
    test_volume_entity._attr_entity_category = EntityCategory.DIAGNOSTIC
    entities.append(test_volume_entity)

    async_add_entities(entities)


class BaseMasjidNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, name: str, unique_id: str, entry: ConfigEntry, coordinator) -> None:
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._entry = entry
        self._coordinator = coordinator
        self._value: float | None = None

        # Add device info for proper grouping - same pattern as sensor entities
        self._attr_device_info = coordinator.get_device_info()

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        await self._save_value()
        self.async_write_ha_state()

    async def _save_value(self) -> None:
        """Save the current value to config entry options."""
        options = dict(self._entry.options)
        options[self._get_config_key()] = self._value
        self.hass.config_entries.async_update_entry(self._entry, options=options)

    def _get_config_key(self) -> str:
        """Get the config key for this entity's value."""
        raise NotImplementedError


class AzanVolumeNumber(BaseMasjidNumber):
    _attr_native_min_value = VOLUME_MIN
    _attr_native_max_value = VOLUME_MAX
    _attr_native_step = VOLUME_STEPS
    _attr_mode = "slider"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:volume-high"

    def __init__(self, name: str, unique_id: str, entry: ConfigEntry, prayer: str, coordinator) -> None:
        super().__init__(name, unique_id, entry, coordinator)
        self._prayer = prayer
        # Load saved value or use default
        self._value = entry.options.get(self._get_config_key(), 50)

    def _get_config_key(self) -> str:
        prayer_to_config = {
            "fajr": CONF_AZAN_VOLUME_FAJR,
            "dhuhr": CONF_AZAN_VOLUME_DHUHR,
            "asr": CONF_AZAN_VOLUME_ASR,
            "maghrib": CONF_AZAN_VOLUME_MAGHRIB,
            "isha": CONF_AZAN_VOLUME_ISHA,
            "test": CONF_AZAN_VOLUME_TEST,
        }
        return prayer_to_config.get(self._prayer, f"azan_volume_{self._prayer}")


class CarStartMinutesNumber(BaseMasjidNumber):
    _attr_native_min_value = CAR_WATER_MINUTES_MIN
    _attr_native_max_value = CAR_WATER_MINUTES_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer"

    def __init__(self, name: str, unique_id: str, entry: ConfigEntry, coordinator) -> None:
        super().__init__(name, unique_id, entry, coordinator)
        # Load saved value or use default
        self._value = entry.options.get(CONF_CAR_START_MINUTES, CAR_START_MINUTES_DEFAULT)

    def _get_config_key(self) -> str:
        return CONF_CAR_START_MINUTES


class WaterRecircMinutesNumber(BaseMasjidNumber):
    _attr_native_min_value = CAR_WATER_MINUTES_MIN
    _attr_native_max_value = CAR_WATER_MINUTES_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer"

    def __init__(self, name: str, unique_id: str, entry: ConfigEntry, coordinator) -> None:
        super().__init__(name, unique_id, entry, coordinator)
        # Load saved value or use default
        self._value = entry.options.get(CONF_WATER_RECIRC_MINUTES, WATER_RECIRC_MINUTES_DEFAULT)

    def _get_config_key(self) -> str:
        return CONF_WATER_RECIRC_MINUTES


class RamadanReminderMinutesNumber(BaseMasjidNumber):
    _attr_native_min_value = RAMADAN_REMINDER_MIN
    _attr_native_max_value = RAMADAN_REMINDER_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer"

    def __init__(self, name: str, unique_id: str, entry: ConfigEntry, coordinator) -> None:
        super().__init__(name, unique_id, entry, coordinator)
        # Load saved value or use default
        self._value = entry.options.get(CONF_RAMADAN_REMINDER_MINUTES, RAMADAN_REMINDER_MINUTES_DEFAULT)

    def _get_config_key(self) -> str:
        return CONF_RAMADAN_REMINDER_MINUTES





