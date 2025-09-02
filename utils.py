"""Utility functions for The Masjid App integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def get_number(hass: HomeAssistant, entity_id: str, default_val: float) -> float:
    """Get the value of a number entity."""
    _LOGGER.debug("Getting number value for entity: %s", entity_id)

    st = hass.states.get(entity_id)
    if not st:
        _LOGGER.warning("Entity not found: %s, returning default: %s", entity_id, default_val)
        return default_val

    _LOGGER.debug("Entity %s found - state: '%s', attributes: %s", entity_id, st.state, st.attributes)

    try:
        result = float(st.state)
        _LOGGER.debug("Successfully converted state '%s' to float: %s", st.state, result)
        return result
    except Exception as e:  # noqa: BLE001
        _LOGGER.warning("Failed to convert state '%s' to float for entity %s: %s, returning default: %s",
                       st.state, entity_id, e, default_val)
        return default_val


def get_switch_state(hass: HomeAssistant, entity_id: str, default_val: bool = False) -> bool:
    """Get the state of a switch entity."""
    _LOGGER.debug("Getting switch state for entity: %s", entity_id)

    st = hass.states.get(entity_id)
    if not st:
        _LOGGER.warning("Entity not found: %s, returning default: %s", entity_id, default_val)
        return default_val

    _LOGGER.debug("Entity %s found - state: '%s' (type: %s), attributes: %s",
                 entity_id, st.state, type(st.state).__name__, st.attributes)

    result = st.state == "on"
    _LOGGER.debug("Switch state comparison: '%s' == 'on' = %s", st.state, result)

    return result


def all_presence_sensors_present(hass: HomeAssistant, presence_entities: list[str]) -> bool:
    """Check if all selected presence sensors indicate presence."""
    _LOGGER.debug("Checking presence for entities: %s", presence_entities)

    if not presence_entities:
        _LOGGER.debug("No presence entities configured, assuming present")
        return True  # If no sensors selected, assume present

    for entity_id in presence_entities:
        state = hass.states.get(entity_id)
        if not state:
            _LOGGER.warning("Presence entity not found, skipping: %s", entity_id)
            continue  # Skip missing entities

        _LOGGER.debug("Checking presence entity %s - state: '%s'", entity_id, state.state)

        # Handle different entity types
        if entity_id.startswith("binary_sensor."):
            # For binary sensors, check if state is "on"
            if state.state != "on":
                _LOGGER.debug("Binary sensor %s not present (state: '%s')", entity_id, state.state)
                return False
        elif entity_id.startswith("device_tracker."):
            # For device trackers, check if state is "home"
            if state.state != "home":
                _LOGGER.debug("Device tracker %s not home (state: '%s')", entity_id, state.state)
                return False
        elif entity_id.startswith("person."):
            # For person entities, check if state is "home"
            if state.state != "home":
                _LOGGER.debug("Person %s not home (state: '%s')", entity_id, state.state)
                return False

    _LOGGER.debug("All presence sensors indicate presence")
    return True
