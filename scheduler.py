from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_change, async_call_later

from .const import (
    PRAYERS,
    AZAN_NAME_MAP,
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
    ENTITY_KEY_CAR_START_MINUTES,
    ENTITY_KEY_WATER_RECIRC_MINUTES,
    ENTITY_KEY_RAMADAN_REMINDER_MINUTES,
    ENTITY_KEY_AZAN_VOLUME_BASE,
    ENTITY_KEY_AZAN_ENABLED,
    ENTITY_KEY_CAR_START_ENABLED,
    ENTITY_KEY_WATER_RECIRC_ENABLED,
    ENTITY_KEY_RAMADAN_REMINDER_ENABLED,
    CAR_START_MINUTES_DEFAULT,
    WATER_RECIRC_MINUTES_DEFAULT,
    RAMADAN_REMINDER_MINUTES_DEFAULT,
    AZAN_VOLUME_DEFAULT,
)
from .helpers import parse_prayer_time, MasjidEntityRegistry
from .utils import all_presence_sensors_present

_LOGGER = logging.getLogger(__name__)


class MasjidScheduler:
    def __init__(self, hass: HomeAssistant, entry_options: dict[str, Any], coordinator, entity_registry: MasjidEntityRegistry) -> None:
        self.hass: HomeAssistant = hass
        self.entry_options: dict[str, Any] = entry_options
        self._coordinator = coordinator
        self._entity_registry: MasjidEntityRegistry = entity_registry
        self._handles: list[CALLBACK_TYPE] = []

    def clear_schedules(self) -> None:
        _LOGGER.debug("Clearing %d existing schedules", len(self._handles))
        for h in self._handles:
            h()  # Home Assistant handles cleanup gracefully
        self._handles.clear()
        _LOGGER.debug("All schedules cleared")

    def schedule_from_data(self, data: dict[str, Any]) -> None:
        self.clear_schedules()
        masjid: dict[str, Any] = data.get("masjid", {})
        azan_times: dict[str, str] = masjid.get("azan", {})
        _LOGGER.debug("Starting azan scheduling process")
        _LOGGER.debug("Received masjid data: %s", masjid)
        _LOGGER.debug("Available azan times: %s", azan_times)

        now = datetime.now()
        _LOGGER.debug("Current time: %s", now)

        for p in PRAYERS:
            masjid_key = AZAN_NAME_MAP[p]

            # Schedule Azan
            azan_txt = azan_times.get(masjid_key)
            _LOGGER.debug("Processing prayer '%s' (API key: '%s'), azan text: '%s'", p, masjid_key, azan_txt)

            if azan_txt:
                azan_dt = parse_prayer_time(azan_txt)
                if azan_dt:
                    # Use a lambda that captures p by value
                    handle = async_track_time_change(
                        self.hass,
                        lambda _now, prayer=p: self.hass.add_job(self._handle_azan, prayer),
                        hour=azan_dt.hour,
                        minute=azan_dt.minute,
                        second=0
                    )
                    self._handles.append(handle)
                    _LOGGER.info("Successfully scheduled azan for %s at %s", p, azan_dt.strftime("%I:%M %p"))
                else:
                    _LOGGER.warning("Skipping azan scheduling for %s due to invalid time format: %s", p, azan_txt)
            else:
                _LOGGER.debug("No azan time found for prayer '%s', skipping", p)

            # Schedule Prayer-based actions (Car Start, Water Recirculation, etc.)
            prayer_txt: str = masjid.get(masjid_key, "")
            if not prayer_txt:
                continue

            prayer_dt = parse_prayer_time(prayer_txt)
            if prayer_dt is None:
                _LOGGER.warning("Skipping prayer time scheduling for %s due to invalid time format: %s", p, prayer_txt)
                continue

            # Car start offset minutes - use live value from number entity
            car_mins_entity = self._entity_registry.get_entity(ENTITY_KEY_CAR_START_MINUTES)
            car_mins = max(0, int(car_mins_entity.native_value if car_mins_entity else CAR_START_MINUTES_DEFAULT))

            if car_mins > 0:
                car_time = prayer_dt - timedelta(minutes=car_mins)
                handle = async_track_time_change(
                    self.hass,
                    lambda _now: self.hass.add_job(self._handle_car_start),
                    hour=car_time.hour,
                    minute=car_time.minute,
                    second=0
                )
                self._handles.append(handle)

            # Water recirculation offset minutes - use live value from number entity
            water_mins_entity = self._entity_registry.get_entity(ENTITY_KEY_WATER_RECIRC_MINUTES)
            water_mins = max(0, int(water_mins_entity.native_value if water_mins_entity else WATER_RECIRC_MINUTES_DEFAULT))

            if water_mins > 0:
                water_time = prayer_dt - timedelta(minutes=water_mins)
                handle = async_track_time_change(
                    self.hass,
                    lambda _now: self.hass.add_job(self._handle_water_recirc),
                    hour=water_time.hour,
                    minute=water_time.minute,
                    second=0
                )
                self._handles.append(handle)

            # Ramadan reminder only for maghrib; offset minutes - use live value from number entity
            if p == "maghrib":
                rem_mins_entity = self._entity_registry.get_entity(ENTITY_KEY_RAMADAN_REMINDER_MINUTES)
                rem_mins = max(0, int(rem_mins_entity.native_value if rem_mins_entity else RAMADAN_REMINDER_MINUTES_DEFAULT))

                if rem_mins > 0:
                    rem_time = prayer_dt - timedelta(minutes=rem_mins)
                    handle = async_track_time_change(
                        self.hass,
                        lambda _now: self.hass.add_job(self._handle_ramadan_reminder),
                        hour=rem_time.hour,
                        minute=rem_time.minute,
                        second=0
                    )
                    self._handles.append(handle)

        _LOGGER.info("Finished scheduling Azan and prayer callbacks")

    def _get_azan_volume(self, prayer: str) -> int:
        """Get the azan volume for a specific prayer from live entity state."""
        entity = self._entity_registry.get_entity(f"{ENTITY_KEY_AZAN_VOLUME_BASE}_{prayer}")
        return int(entity.native_value if entity else AZAN_VOLUME_DEFAULT)

    async def _prepare_media_playback(self, media_player: str, volume_percent: int, context: str) -> float:
        """
        Prepare media player for playback with volume management.

        Args:
            media_player: Entity ID of the media player
            volume_percent: Target volume percentage (0-100)
            context: Context for logging (e.g., 'azan', 'reminder')

        Returns:
            Previous volume level
        """

        # Save current volume
        media_player_current_state = self.hass.states.get(media_player)
        _LOGGER.debug("Media player (%s) current state: %s", media_player,
                     media_player_current_state.state if media_player_current_state else "Not found")

        previous_volume = (media_player_current_state and media_player_current_state.attributes.get("volume_level")) or 0.5
        volume_level = max(0.0, min(1.0, volume_percent / 100.0))

        _LOGGER.debug("%s volume settings - Previous: %.2f, Target: %.2f (from %s%%)",
                     context.title(), previous_volume, volume_level, volume_percent)

        # Stop if playing
        if media_player_current_state and media_player_current_state.state == "playing":
            _LOGGER.debug("Media player is currently playing, stopping it first")
            await self.hass.services.async_call("media_player", "media_stop", {"entity_id": media_player}, blocking=True)
            await asyncio.sleep(1)

        # Set volume
        _LOGGER.debug("Setting volume to %.2f on %s for %s", volume_level, media_player, context)
        await self.hass.services.async_call("media_player", "volume_set", {"entity_id": media_player, "volume_level": volume_level}, blocking=True)
        return previous_volume

    async def _restore_volume_and_resume(self, media_player: str, previous_volume: float,
                                       paused_players: list[str] | None = None, delay_seconds: int = 0) -> None:
        """
        Restore volume and resume paused players after a delay.

        Args:
            media_player: Entity ID of the media player
            previous_volume: Volume level to restore
            paused_players: List of paused player entity IDs to resume
            delay_seconds: Delay before restoration (0 for immediate)
        """
        async def _restore() -> None:
            await self.hass.services.async_call("media_player", "volume_set", {"entity_id": media_player, "volume_level": float(previous_volume)}, blocking=False)
            _LOGGER.debug("Restored volume to %.2f on %s", previous_volume, media_player)

            if paused_players:
                for p in paused_players:
                    await self.hass.services.async_call("media_player", "media_play", {"entity_id": p}, blocking=False)
                _LOGGER.debug("Resumed %d paused players", len(paused_players))

        if delay_seconds > 0:
            async_call_later(self.hass, delay_seconds, lambda _time: self.hass.add_job(_restore))
        else:
            await _restore()

    # Handlers
    async def _handle_azan(self, prayer: str) -> None:
        _LOGGER.info("Azan handler triggered for prayer: %s", prayer)

        # Check if azan is enabled using live switch state (skip check for test calls)
        if prayer != "test":
            azan_switch = self._entity_registry.get_entity(ENTITY_KEY_AZAN_ENABLED)
            azan_enabled = azan_switch.is_on if azan_switch else True
            _LOGGER.debug("Azan enabled switch state: %s", azan_enabled)
            if not azan_enabled:
                _LOGGER.info("Azan is disabled via switch, skipping azan for %s", prayer)
                return

        # Volume per prayer - use live value from number entity
        vol_percent = self._get_azan_volume(prayer)
        _LOGGER.debug("Azan volume for %s: %s%%", prayer, vol_percent)

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

        # Prepare media player for playback
        previous_volume = await self._prepare_media_playback(media_player, vol_percent, "azan")

        # Play azan
        _LOGGER.info("Playing azan for %s - Content: %s, Volume: %s%%, Duration: %ss",
                    prayer, content_id, vol_percent, duration)
        await self.hass.services.async_call(
            "media_player",
            "play_media",
            {"entity_id": media_player, "media_content_type": "music", "media_content_id": content_id, "announce": True},
            blocking=False,
        )
        _LOGGER.debug("Azan playback initiated successfully for %s", prayer)

        # Pause other players periodically for duration
        pause_players = self.entry_options.get(CONF_MEDIA_PLAYERS_TO_PAUSE, [])
        paused: list[str] = []
        if pause_players:
            for p in pause_players:
                st = self.hass.states.get(p)
                if st and st.state == "playing":
                    await self.hass.services.async_call("media_player", "media_pause", {"entity_id": p}, blocking=False)
                    paused.append(p)

        # Restore volume and resume after duration
        if duration > 0:
            await self._restore_volume_and_resume(media_player, previous_volume, paused, duration)

    async def _handle_car_start(self) -> None:
        _LOGGER.debug("Car start handler triggered")

        # Check if car start is enabled using live switch state
        car_switch = self._entity_registry.get_entity(ENTITY_KEY_CAR_START_ENABLED)
        car_enabled = car_switch.is_on if car_switch else False
        _LOGGER.debug("Car start enabled switch state: %s", car_enabled)

        if not car_enabled:
            _LOGGER.debug("Car start is disabled via switch, skipping")
            return

        presence_entities = self.entry_options.get(CONF_PRESENCE_SENSORS, [])
        _LOGGER.debug("Checking presence sensors: %s", presence_entities)

        presence_detected = all_presence_sensors_present(self.hass, presence_entities)
        _LOGGER.debug("Presence sensors status: %s", presence_detected)

        if not presence_detected:
            _LOGGER.debug("Not all presence sensors are present, skipping car start")
            return

        svc = self.entry_options.get(CONF_ACTION_CAR_START)
        _LOGGER.debug("Car start service configuration: %s", svc)

        if not svc:
            _LOGGER.debug("No car start service configured, skipping")
            return

        domain, _, service = svc.partition(".")
        _LOGGER.debug("Car start service - Domain: %s, Service: %s", domain, service)

        # ObjectSelector returns a dict, fallback to empty dict if not set
        data = self.entry_options.get(CONF_ACTION_CAR_START_PARAMS) or {}
        _LOGGER.debug("Car start service parameters: %s", data)

        _LOGGER.info("Executing car start service: %s.%s with data: %s", domain, service, data)
        await self.hass.services.async_call(domain, service, data, blocking=False)
        _LOGGER.debug("Car start service call completed successfully")

    async def _handle_water_recirc(self) -> None:
        _LOGGER.debug("Water recirculation handler triggered")

        # Check if water recirculation is enabled using live switch state
        water_switch = self._entity_registry.get_entity(ENTITY_KEY_WATER_RECIRC_ENABLED)
        recirc_enabled = water_switch.is_on if water_switch else False
        _LOGGER.debug("Water recirculation enabled switch state: %s", recirc_enabled)

        if not recirc_enabled:
            _LOGGER.debug("Water recirculation is disabled via switch, skipping")
            return

        presence_entities = self.entry_options.get(CONF_PRESENCE_SENSORS, [])
        _LOGGER.debug("Checking presence sensors: %s", presence_entities)

        presence_detected = all_presence_sensors_present(self.hass, presence_entities)
        _LOGGER.debug("Presence sensors status: %s", presence_detected)

        if not presence_detected:
            _LOGGER.debug("Not all presence sensors are present, skipping water recirculation")
            return

        svc = self.entry_options.get(CONF_ACTION_WATER_RECIRCULATION)
        _LOGGER.debug("Water recirculation service configuration: %s", svc)

        if not svc:
            _LOGGER.debug("No water recirculation service configured, skipping")
            return

        domain, _, service = svc.partition(".")
        _LOGGER.debug("Water recirculation service - Domain: %s, Service: %s", domain, service)

        # ObjectSelector returns a dict, fallback to empty dict if not set
        data = self.entry_options.get(CONF_ACTION_WATER_RECIRCULATION_PARAMS) or {}
        _LOGGER.debug("Water recirculation service parameters: %s", data)

        _LOGGER.info("Executing water recirculation service: %s.%s with data: %s", domain, service, data)
        await self.hass.services.async_call(domain, service, data, blocking=False)
        _LOGGER.debug("Water recirculation service call completed successfully")

    async def _handle_ramadan_reminder(self) -> None:
        _LOGGER.debug("Ramadan reminder handler triggered")

        # Check if ramadan reminder is enabled using live switch state
        ramadan_switch = self._entity_registry.get_entity(ENTITY_KEY_RAMADAN_REMINDER_ENABLED)
        ramadan_on = ramadan_switch.is_on if ramadan_switch else False
        _LOGGER.debug("Ramadan reminder switch state: %s", ramadan_on)

        if not ramadan_on:
            _LOGGER.debug("Ramadan reminder is disabled via switch, skipping")
            return

        tts = self.entry_options.get(CONF_TTS_ENTITY)
        media_player = self.entry_options.get(CONF_MEDIA_PLAYER)
        _LOGGER.debug("TTS entity: %s, Media player: %s", tts, media_player)

        if not tts or not media_player or tts == "" or media_player == "":
            _LOGGER.debug("Invalid TTS or media player configuration, skipping ramadan reminder")
            return

        # Get maghrib azan volume for reminder
        vol_percent = self._get_azan_volume("maghrib")
        _LOGGER.debug("Reminder volume (using maghrib azan volume): %s%%", vol_percent)

        # Use live value from number entity
        mins_entity = self._entity_registry.get_entity(ENTITY_KEY_RAMADAN_REMINDER_MINUTES)
        mins = int(mins_entity.native_value if mins_entity else 2.0)
        _LOGGER.debug("Ramadan reminder minutes: %s", mins)

        minute_word = "minute" if mins == 1 else "minutes"
        message = f"Maghrib prayer will start in {mins} {minute_word}"
        _LOGGER.debug("Generated reminder message: %s", message)

        # Prepare media player for playback
        _LOGGER.debug("Preparing media player for ramadan reminder playback")
        previous_volume = await self._prepare_media_playback(media_player, vol_percent, "reminder")

        # Play reminder message
        _LOGGER.info("Playing ramadan reminder - Message: %s, Volume: %s%%", message, vol_percent)
        await self.hass.services.async_call(
            "tts",
            "speak",
            {"entity_id": tts, "cache": True, "message": message, "media_player_entity_id": media_player},
            blocking=False,
        )
        _LOGGER.debug("Ramadan reminder TTS service call completed successfully")

        # Restore volume after a short delay (TTS typically takes a few seconds)
        _LOGGER.debug("Scheduling volume restoration after 5 seconds")
        await self._restore_volume_and_resume(media_player, previous_volume, delay_seconds=5)
