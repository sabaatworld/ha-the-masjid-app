"""Utility functions for The Masjid App integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


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
