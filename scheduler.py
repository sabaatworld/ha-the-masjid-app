from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_change, async_call_later

from .const import (
    PRAYERS,
    CONF_MEDIA_PLAYER,
    CONF_MEDIA_DATA,
    CONF_MEDIA_CONTENT_LENGTH,
    CONF_MEDIA_PLAYERS_TO_PAUSE,
    CONF_ACTION_WATER_RECIRCULATION,
    CONF_ACTION_WATER_RECIRCULATION_PARAMS,
    CONF_ACTION_CAR_START,
    CONF_ACTION_CAR_START_PARAMS,
    CONF_PRESENCE_SENSORS,
    CONF_TTS_ENTITY,
)
from .helpers import parse_prayer_time

_LOGGER = logging.getLogger(__name__)


class MasjidScheduler:
    def __init__(self, hass: HomeAssistant, entry_options: dict[str, Any], coordinator) -> None:
        self.hass: HomeAssistant = hass
        self.entry_options: dict[str, Any] = entry_options
        self._coordinator = coordinator
        self._handles: list[CALLBACK_TYPE] = []

    def clear_schedules(self) -> None:
        _LOGGER.debug("Clearing %d existing schedules", len(self._handles))
        for h in self._handles:
            try:
                h()
            except Exception:  # noqa: BLE001
                pass
        self._handles.clear()
        _LOGGER.debug("All schedules cleared")

    def schedule_from_data(self, data: dict[str, Any]) -> None:
        self.clear_schedules()
        masjid: dict[str, Any] = data.get("masjid", {})
        azan_times: dict[str, str] = masjid.get("azan", {})
        # Map to appdaemon naming
        name_map: dict[str, str] = {"fajr": "fajr", "dhuhr": "zuhr", "asr": "asr", "maghrib": "maghrib", "isha": "isha"}

        _LOGGER.debug("Starting azan scheduling process")
        _LOGGER.debug("Received masjid data: %s", masjid)
        _LOGGER.debug("Available azan times: %s", azan_times)

        now = datetime.now()
        _LOGGER.debug("Current time: %s", now)

        scheduled_count = 0
        for p in PRAYERS:
            masjid_key = name_map[p]
            azan_txt = azan_times.get(masjid_key)
            _LOGGER.debug("Processing prayer '%s' (API key: '%s'), azan text: '%s'", p, masjid_key, azan_txt)

            if not azan_txt:
                _LOGGER.debug("No azan time found for prayer '%s', skipping", p)
                continue

            try:
                azan_dt = parse_prayer_time(azan_txt)

                # Use async_track_time_change for daily repetition - much simpler!
                def azan_callback(_now):
                    self.hass.async_create_task(self._handle_azan(p))

                handle = async_track_time_change(
                    self.hass,
                    azan_callback,
                    hour=azan_dt.hour,
                    minute=azan_dt.minute,
                    second=0
                )
                self._handles.append(handle)
                scheduled_count += 1
                _LOGGER.info("Successfully scheduled azan for %s at %s", p, azan_dt.strftime("%I:%M %p"))

            except Exception as e:
                _LOGGER.error("Failed to schedule azan for prayer '%s' with time '%s': %s", p, azan_txt, e)

        _LOGGER.info("Azan scheduling completed. Successfully scheduled %d out of %d prayers",
                    scheduled_count, len(PRAYERS))

        # For prayer times, use masjid[<prayer>] keys (zuhr for dhuhr)
        for p in PRAYERS:
            masjid_key = name_map[p]
            prayer_txt: str = masjid.get(masjid_key, "")
            fallback_azan_txt = azan_times.get(masjid_key)
            if not prayer_txt and not fallback_azan_txt:
                continue
            target_dt = parse_prayer_time(prayer_txt or fallback_azan_txt)
            target_at = now.replace(hour=target_dt.hour, minute=target_dt.minute, second=0, microsecond=0)
            if target_at <= now:
                target_at += timedelta(days=1)

            # Car start offset minutes - use live value from number entity
            prefix = self._coordinator.get_sanitized_mosque_prefix()
            car_mins_entity = f"number.{prefix}_car_start_minutes"
            car_mins = max(0, int(self._get_number(car_mins_entity, 10.0)))

            if car_mins > 0:
                car_time = target_dt - timedelta(minutes=car_mins)
                def car_callback(_now):
                    self.hass.async_create_task(self._handle_car_start())

                handle = async_track_time_change(
                    self.hass,
                    car_callback,
                    hour=car_time.hour,
                    minute=car_time.minute,
                    second=0
                )
                self._handles.append(handle)

            # Water recirculation offset minutes - use live value from number entity
            water_mins_entity = f"number.{prefix}_water_recirc_minutes"
            water_mins = max(0, int(self._get_number(water_mins_entity, 15.0)))

            if water_mins > 0:
                water_time = target_dt - timedelta(minutes=water_mins)
                def water_callback(_now):
                    self.hass.async_create_task(self._handle_water_recirc())

                handle = async_track_time_change(
                    self.hass,
                    water_callback,
                    hour=water_time.hour,
                    minute=water_time.minute,
                    second=0
                )
                self._handles.append(handle)

            # Ramadan reminder only for maghrib; offset minutes - use live value from number entity
            if p == "maghrib":
                rem_mins_entity = f"number.{prefix}_ramadan_reminder_minutes"
                rem_mins = max(0, int(self._get_number(rem_mins_entity, 2.0)))

                if rem_mins > 0:
                    rem_time = target_dt - timedelta(minutes=rem_mins)
                    def ramadan_callback(_now):
                        self.hass.async_create_task(self._handle_ramadan_reminder())

                    handle = async_track_time_change(
                        self.hass,
                        ramadan_callback,
                        hour=rem_time.hour,
                        minute=rem_time.minute,
                        second=0
                    )
                    self._handles.append(handle)



    # Utilities to read states
    def _is_on(self, entity_id: str) -> bool:
        st = self.hass.states.get(entity_id)
        return bool(st and st.state == "on")

    def _get_switch_state(self, entity_id: str, default_val: bool = False) -> bool:
        """Get the state of a switch entity."""
        st = self.hass.states.get(entity_id)
        if not st:
            return default_val
        return st.state == "on"

    def _all_presence_sensors_present(self, presence_entities: list[str]) -> bool:
        """Check if all selected presence sensors indicate presence."""
        if not presence_entities:
            return True  # If no sensors selected, assume present

        for entity_id in presence_entities:
            state = self.hass.states.get(entity_id)
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

    def _get_number(self, entity_id: str, default_val: float) -> float:
        st = self.hass.states.get(entity_id)
        if not st:
            return default_val
        try:
            return float(st.state)
        except Exception:  # noqa: BLE001
            return default_val

    def _get_azan_volume(self, prayer: str) -> int:
        """Get the azan volume for a specific prayer from live entity state."""
        prefix = self._coordinator.get_sanitized_mosque_prefix()
        entity_id = f"number.{prefix}_{prayer}_azan_volume"
        return int(self._get_number(entity_id, 50.0))

    # Handlers
    async def _handle_azan(self, prayer: str) -> None:
        _LOGGER.info("Azan handler triggered for prayer: %s", prayer)

        # Check if azan is enabled using live switch state (skip check for test calls)
        if prayer != "test":
            prefix = self._coordinator.get_sanitized_mosque_prefix()
            azan_switch_id = f"switch.{prefix}_azan_enabled"
            azan_enabled = self._get_switch_state(azan_switch_id, True)
            _LOGGER.debug("Azan enabled switch (%s) state: %s", azan_switch_id, azan_enabled)
            if not azan_enabled:
                _LOGGER.info("Azan is disabled via switch, skipping azan for %s", prayer)
                return

        # Volume per prayer - use live value from number entity
        vol_percent = self._get_azan_volume(prayer)
        _LOGGER.debug("Azan volume for %s: %s%%", prayer, vol_percent)
        if vol_percent <= 0:
            _LOGGER.info("Azan volume is 0 for %s, skipping azan", prayer)
            return

        media_player = self.entry_options.get(CONF_MEDIA_PLAYER)
        media_data = self.entry_options.get(CONF_MEDIA_DATA, {})
        content_id = media_data.get("media_content_id", "")
        duration = int(self.entry_options.get(CONF_MEDIA_CONTENT_LENGTH, 0) or 0)

        _LOGGER.debug("Media configuration - Player: %s, Content ID: %s, Duration: %s",
                     media_player, content_id, duration)

        if not media_player or not content_id or media_player == "":
            _LOGGER.error("Invalid media configuration - Player: %s, Content ID: %s",
                         media_player, content_id)
            return

        # Save current volume
        media_player_current_state = self.hass.states.get(media_player)
        _LOGGER.debug("Media player (%s) current state: %s", media_player,
                     media_player_current_state.state if media_player_current_state else "Not found")

        previous_volume = (media_player_current_state and media_player_current_state.attributes.get("volume_level")) or 0.5
        volume_level = max(0.0, min(1.0, vol_percent / 100.0))

        _LOGGER.debug("Volume settings - Previous: %.2f, Target: %.2f (from %s%%)",
                     previous_volume, volume_level, vol_percent)

        # Stop if playing
        if media_player_current_state and media_player_current_state.state == "playing":
            _LOGGER.debug("Media player is currently playing, stopping it first")
            await self.hass.services.async_call("media_player", "media_stop", {"entity_id": media_player}, blocking=True)
            await asyncio.sleep(1)

        # Set volume, then play
        try:
            _LOGGER.debug("Setting volume to %.2f on %s", volume_level, media_player)
            await self.hass.services.async_call("media_player", "volume_set", {"entity_id": media_player, "volume_level": volume_level}, blocking=True)

            _LOGGER.info("Playing azan for %s - Content: %s, Volume: %s%%, Duration: %ss",
                        prayer, content_id, vol_percent, duration)
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {"entity_id": media_player, "media_content_type": "music", "media_content_id": content_id, "announce": True},
                blocking=False,
            )
            _LOGGER.debug("Azan playback initiated successfully for %s", prayer)

        except Exception as e:
            _LOGGER.error("Failed to play azan for %s: %s", prayer, e)
            return

        # Pause other players periodically for duration
        pause_players = self.entry_options.get(CONF_MEDIA_PLAYERS_TO_PAUSE, [])
        paused: list[str] = []
        if pause_players:
            for p in pause_players:
                st = self.hass.states.get(p)
                if st and st.state == "playing":
                    await self.hass.services.async_call("media_player", "media_pause", {"entity_id": p}, blocking=False)
                    paused.append(p)

        # Restore volume and resume after duration using async_call_later - much simpler!
        if duration > 0:
            async def _restore() -> None:
                await self.hass.services.async_call("media_player", "volume_set", {"entity_id": media_player, "volume_level": float(previous_volume)}, blocking=False)
                for p in paused:
                    await self.hass.services.async_call("media_player", "media_play", {"entity_id": p}, blocking=False)

            async_call_later(self.hass, duration, lambda: self.hass.async_create_task(_restore()))

    async def _handle_car_start(self) -> None:
        # Check if car start is enabled using live switch state
        prefix = self._coordinator.get_sanitized_mosque_prefix()
        car_switch_id = f"switch.{prefix}_car_start_enabled"
        car_enabled = self._get_switch_state(car_switch_id, False)
        if not car_enabled:
            return
        presence_entities = self.entry_options.get(CONF_PRESENCE_SENSORS, [])
        if not self._all_presence_sensors_present(presence_entities):
            return
        svc = self.entry_options.get(CONF_ACTION_CAR_START)
        if not svc:
            return
        domain, _, service = svc.partition(".")
        # ObjectSelector returns a dict, fallback to empty dict if not set
        data = self.entry_options.get(CONF_ACTION_CAR_START_PARAMS) or {}
        await self.hass.services.async_call(domain, service, data, blocking=False)

    async def _handle_water_recirc(self) -> None:
        # Check if water recirculation is enabled using live switch state
        prefix = self._coordinator.get_sanitized_mosque_prefix()
        water_switch_id = f"switch.{prefix}_water_recirc_enabled"
        recirc_enabled = self._get_switch_state(water_switch_id, False)
        if not recirc_enabled:
            return
        presence_entities = self.entry_options.get(CONF_PRESENCE_SENSORS, [])
        if not self._all_presence_sensors_present(presence_entities):
            return
        svc = self.entry_options.get(CONF_ACTION_WATER_RECIRCULATION)
        if not svc:
            return
        domain, _, service = svc.partition(".")
        # ObjectSelector returns a dict, fallback to empty dict if not set
        data = self.entry_options.get(CONF_ACTION_WATER_RECIRCULATION_PARAMS) or {}
        await self.hass.services.async_call(domain, service, data, blocking=False)

    async def _handle_ramadan_reminder(self) -> None:
        # Check if ramadan reminder is enabled using live switch state
        prefix = self._coordinator.get_sanitized_mosque_prefix()
        ramadan_switch_id = f"switch.{prefix}_ramadan_reminder"
        ramadan_on = self._get_switch_state(ramadan_switch_id, False)
        if not ramadan_on:
            return
        tts = self.entry_options.get(CONF_TTS_ENTITY)
        media_player = self.entry_options.get(CONF_MEDIA_PLAYER)
        if not tts or not media_player or tts == "" or media_player == "":
            return
        # Use live value from number entity
        mins_entity_id = f"number.{prefix}_ramadan_reminder_minutes"
        mins = int(self._get_number(mins_entity_id, 2.0))
        minute_word = "minute" if mins == 1 else "minutes"
        message = f"Maghrib prayer will start in {mins} {minute_word}"
        await self.hass.services.async_call(
            "tts",
            "speak",
            {"entity_id": tts, "cache": True, "message": message, "media_player_entity_id": media_player},
            blocking=False,
        )

    def attach_listeners(self) -> None:
        """No longer needed - scheduler now reads live entity states directly."""
        pass


