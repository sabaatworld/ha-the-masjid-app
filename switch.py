from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_AZAN_ENABLED,
    CONF_RAMADAN_REMINDER_ENABLED,
    CONF_CAR_START_ENABLED,
    CONF_WATER_RECIRC_ENABLED,
)


class BaseMasjidSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, unique_id: str, entry: ConfigEntry, coordinator, default: bool = False) -> None:
        self._attr_unique_id = unique_id
        self._entry = entry
        self._coordinator = coordinator
        self._is_on = entry.options.get(self._get_config_key(), default)
        self._attr_icon = "mdi:toggle-switch"

        # Add device info for proper grouping - same pattern as sensor entities
        self._attr_device_info = coordinator.get_device_info()

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        self._is_on = True
        await self._save_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003
        self._is_on = False
        await self._save_state()
        self.async_write_ha_state()

    async def _save_state(self) -> None:
        """Save the current state to config entry options."""
        options = dict(self._entry.options)
        options[self._get_config_key()] = self._is_on
        self.hass.config_entries.async_update_entry(self._entry, options=options)

    def _get_config_key(self) -> str:
        """Get the config key for this entity's state."""
        raise NotImplementedError


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    # Get coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get sanitized prefix for entity IDs
    prefix = coordinator.get_effective_mosque_name()

    entities: list[SwitchEntity] = []
    azan_switch = AzanSwitch(f"{prefix}_{CONF_AZAN_ENABLED}", entry, coordinator, default=True)
    azan_switch._attr_icon = "mdi:volume-high"
    entities.append(azan_switch)

    ramadan_switch = RamadanReminderSwitch(f"{prefix}_{CONF_RAMADAN_REMINDER_ENABLED}", entry, coordinator, default=False)
    ramadan_switch._attr_icon = "mdi:bell-plus"
    entities.append(ramadan_switch)

    car_switch = CarStartSwitch(f"{prefix}_{CONF_CAR_START_ENABLED}", entry, coordinator, default=False)
    car_switch._attr_icon = "mdi:car"
    entities.append(car_switch)

    water_switch = WaterRecircSwitch(f"{prefix}_{CONF_WATER_RECIRC_ENABLED}", entry, coordinator, default=False)
    water_switch._attr_icon = "mdi:water-pump"
    entities.append(water_switch)

    async_add_entities(entities)


class AzanSwitch(BaseMasjidSwitch):
    def __init__(self, unique_id: str, entry: ConfigEntry, coordinator, default: bool = False) -> None:
        super().__init__(unique_id, entry, coordinator, default)
        self._attr_translation_key = "azan"

    def _get_config_key(self) -> str:
        return CONF_AZAN_ENABLED


class RamadanReminderSwitch(BaseMasjidSwitch):
    def __init__(self, unique_id: str, entry: ConfigEntry, coordinator, default: bool = False) -> None:
        super().__init__(unique_id, entry, coordinator, default)
        self._attr_translation_key = "ramadan_reminder"

    def _get_config_key(self) -> str:
        return CONF_RAMADAN_REMINDER_ENABLED


class CarStartSwitch(BaseMasjidSwitch):
    def __init__(self, unique_id: str, entry: ConfigEntry, coordinator, default: bool = False) -> None:
        super().__init__(unique_id, entry, coordinator, default)
        self._attr_translation_key = "car_start"

    def _get_config_key(self) -> str:
        return CONF_CAR_START_ENABLED


class WaterRecircSwitch(BaseMasjidSwitch):
    def __init__(self, unique_id: str, entry: ConfigEntry, coordinator, default: bool = False) -> None:
        super().__init__(unique_id, entry, coordinator, default)
        self._attr_translation_key = "water_recirculation"

    def _get_config_key(self) -> str:
        return CONF_WATER_RECIRC_ENABLED
