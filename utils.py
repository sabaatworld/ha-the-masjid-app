"""Utility functions for The Masjid App integration."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


def get_number(hass: HomeAssistant, entity_id: str, default_val: float) -> float:
    """Get the value of a number entity."""
    st = hass.states.get(entity_id)
    if not st:
        return default_val
    try:
        return float(st.state)
    except Exception:  # noqa: BLE001
        return default_val


def get_switch_state(hass: HomeAssistant, entity_id: str, default_val: bool = False) -> bool:
    """Get the state of a switch entity."""
    st = hass.states.get(entity_id)
    if not st:
        return default_val
    return st.state == "on"


def all_presence_sensors_present(hass: HomeAssistant, presence_entities: list[str]) -> bool:
    """Check if all selected presence sensors indicate presence."""
    if not presence_entities:
        return True  # If no sensors selected, assume present

    for entity_id in presence_entities:
        state = hass.states.get(entity_id)
        if not state:
            continue  # Skip missing entities

        # Handle different entity types
        if entity_id.startswith("binary_sensor."):
            # For binary sensors, check if state is "on"
            if state.state != "on":
                return False
        elif entity_id.startswith("device_tracker."):
            # For device trackers, check if state is "home"
            if state.state != "home":
                return False
        elif entity_id.startswith("person."):
            # For person entities, check if state is "home"
            if state.state != "home":
                return False

    return True
