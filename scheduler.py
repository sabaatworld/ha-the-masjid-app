from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.event import async_track_state_change_event

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
    CONF_AZAN_ENABLED,
    CONF_RAMADAN_REMINDER_ENABLED,
    CONF_CAR_START_ENABLED,
    CONF_WATER_RECIRC_ENABLED,
    CONF_CAR_START_MINUTES,
    CONF_WATER_RECIRC_MINUTES,
    CONF_RAMADAN_REMINDER_MINUTES,
    CONF_AZAN_VOLUME_FAJR,
    CONF_AZAN_VOLUME_DHUHR,
    CONF_AZAN_VOLUME_ASR,
    CONF_AZAN_VOLUME_MAGHRIB,
    CONF_AZAN_VOLUME_ISHA,
)
from .helpers import parse_prayer_time, safe_slug

_LOGGER = logging.getLogger(__name__)


class MasjidScheduler:
    def __init__(self, hass: HomeAssistant, entry_options: dict[str, Any], coordinator) -> None:
        self.hass: HomeAssistant = hass
        self.entry_options: dict[str, Any] = entry_options
        self._coordinator = coordinator
        self._handles: list[CALLBACK_TYPE] = []

    def clear_schedules(self) -> None:
        for h in self._handles:
            try:
                h()
            except Exception:  # noqa: BLE001
                pass
        self._handles.clear()

    def schedule_from_data(self, data: dict[str, Any]) -> None:
        self.clear_schedules()
        masjid: dict[str, Any] = data.get("masjid", {})
        azan_times: dict[str, str] = masjid.get("azan", {})
        # Map to appdaemon naming
        name_map: dict[str, str] = {"fajr": "fajr", "dhuhr": "zuhr", "asr": "asr", "maghrib": "maghrib", "isha": "isha"}

        now = datetime.now()
        for p in PRAYERS:
            masjid_key = name_map[p]
            azan_txt = azan_times.get(masjid_key)
            if not azan_txt:
                continue
            azan_dt = parse_prayer_time(azan_txt)
            azan_at = now.replace(hour=azan_dt.hour, minute=azan_dt.minute, second=0, microsecond=0)
            if azan_at <= now:
                azan_at += timedelta(days=1)
            self._handles.append(self._repeat_daily(azan_at, lambda _p=p: self._handle_azan(_p)))

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

            # Car start offset minutes - use saved value from config
            car_mins = max(0, int(self.entry_options.get(CONF_CAR_START_MINUTES, 10)))
            car_at = target_at - timedelta(minutes=car_mins)
            if car_at <= now:
                car_at += timedelta(days=1)
            self._handles.append(self._repeat_daily(car_at, self._handle_car_start))

            # Water recirculation offset minutes - use saved value from config
            water_mins = max(0, int(self.entry_options.get(CONF_WATER_RECIRC_MINUTES, 15)))
            water_at = target_at - timedelta(minutes=water_mins)
            if water_at <= now:
                water_at += timedelta(days=1)
            self._handles.append(self._repeat_daily(water_at, self._handle_water_recirc))

            # Ramadan reminder only for maghrib; offset minutes - use saved value from config
            if p == "maghrib":
                rem_mins = max(0, int(self.entry_options.get(CONF_RAMADAN_REMINDER_MINUTES, 2)))
                rem_at = target_at - timedelta(minutes=rem_mins)
                if rem_at <= now:
                    rem_at += timedelta(days=1)
                self._handles.append(self._repeat_daily(rem_at, lambda: self._handle_ramadan_reminder()))

    def _repeat_daily(self, first_run: datetime, callback: Callable[[], None]) -> CALLBACK_TYPE:
        def _schedule_next(at: datetime):
            def _wrapped(now):  # noqa: ARG001
                try:
                    self.hass.async_create_task(self._safe_call(callback))
                finally:
                    # schedule next day
                    next_at = at + timedelta(days=1)
                    handle = async_track_point_in_time(self.hass, _make(next_at), next_at)
                    self._handles.append(handle)

            return _wrapped

        def _make(at: datetime):
            return _schedule_next(at)

        handle = async_track_point_in_time(self.hass, _make(first_run), first_run)
        return handle

    async def _safe_call(self, func: Callable[[], None]) -> None:
        try:
            res = func()
            if asyncio.iscoroutine(res):
                await res
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Scheduled task failed")

    # Utilities to read states
    def _is_on(self, entity_id: str) -> bool:
        st = self.hass.states.get(entity_id)
        return bool(st and st.state == "on")

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

    def _slug_prefix(self) -> str:
        mosque: str = self._coordinator.get_effective_mosque_name()
        return safe_slug(mosque)

    def _get_azan_volume(self, prayer: str) -> int:
        """Get the azan volume for a specific prayer from config options."""
        prayer_to_config = {
            "fajr": CONF_AZAN_VOLUME_FAJR,
            "dhuhr": CONF_AZAN_VOLUME_DHUHR,
            "asr": CONF_AZAN_VOLUME_ASR,
            "maghrib": CONF_AZAN_VOLUME_MAGHRIB,
            "isha": CONF_AZAN_VOLUME_ISHA,
        }
        config_key = prayer_to_config.get(prayer, f"azan_volume_{prayer}")
        return self.entry_options.get(config_key, 50)

    # Handlers
    async def _handle_azan(self, prayer: str) -> None:
        # Check if azan is enabled using saved config value
        azan_enabled = self.entry_options.get(CONF_AZAN_ENABLED, True)
        if not azan_enabled:
            return
        # Volume per prayer - use saved value from config
        vol_percent = self._get_azan_volume(prayer)
        if vol_percent <= 0:
            return
        media_player = self.entry_options.get(CONF_MEDIA_PLAYER)
        media_data = self.entry_options.get(CONF_MEDIA_DATA, {})
        content_id = media_data.get("media_content_id", "")
        duration = int(self.entry_options.get(CONF_MEDIA_CONTENT_LENGTH, 0) or 0)
        if not media_player or not content_id or media_player == "":
            return

        # Save current volume
        current_state = self.hass.states.get(media_player)
        current_volume = (current_state and current_state.attributes.get("volume_level")) or 0.5
        volume_level = max(0.0, min(1.0, vol_percent / 100.0))

        # Stop if playing
        if current_state and current_state.state == "playing":
            await self.hass.services.async_call("media_player", "media_stop", {"entity_id": media_player}, blocking=True)

        # Set volume, then play
        await self.hass.services.async_call("media_player", "volume_set", {"entity_id": media_player, "volume_level": volume_level}, blocking=True)
        await self.hass.services.async_call(
            "media_player",
            "play_media",
            {"entity_id": media_player, "media_content_type": "music", "media_content_id": content_id, "announce": True},
            blocking=False,
        )

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
            async def _restore() -> None:
                await self.hass.services.async_call("media_player", "volume_set", {"entity_id": media_player, "volume_level": float(current_volume)}, blocking=False)
                for p in paused:
                    await self.hass.services.async_call("media_player", "media_play", {"entity_id": p}, blocking=False)

            when = datetime.now() + timedelta(seconds=duration)
            async_track_point_in_time(self.hass, lambda _: self.hass.async_create_task(_restore()), when)

    async def _handle_car_start(self) -> None:
        # Check if car start is enabled using saved config value
        car_enabled = self.entry_options.get(CONF_CAR_START_ENABLED, False)
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
        # Check if water recirculation is enabled using saved config value
        recirc_enabled = self.entry_options.get(CONF_WATER_RECIRC_ENABLED, False)
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
        # Check if ramadan reminder is enabled using saved config value
        ramadan_on = self.entry_options.get(CONF_RAMADAN_REMINDER_ENABLED, False)
        if not ramadan_on:
            return
        tts = self.entry_options.get(CONF_TTS_ENTITY)
        media_player = self.entry_options.get(CONF_MEDIA_PLAYER)
        if not tts or not media_player or tts == "" or media_player == "":
            return
        # Use saved value from config
        mins = int(self.entry_options.get(CONF_RAMADAN_REMINDER_MINUTES, 2))
        message = f"Maghrib prayer will start in {mins} minutes"
        await self.hass.services.async_call(
            "tts",
            "speak",
            {"entity_id": tts, "cache": True, "message": message, "media_player_entity_id": media_player},
            blocking=False,
        )

    def attach_listeners(self) -> None:
        """Listen for changes on minute offset numbers and reschedule."""
        slug = self._slug_prefix()
        targets = [
            f"number.{slug}_car_start_minutes",
            f"number.{slug}_water_recirc_minutes",
            f"number.{slug}_ramadan_reminder_minutes",
        ]

        async def _reschedule(event) -> None:  # noqa: ANN001
            # Reschedule with current coordinator data if available
            # We rely on __init__ storing data in hass.data under DOMAIN, but to avoid coupling, we just clear and wait for next coordinator refresh
            # Alternatively, we can rebuild from last schedule if needed; simplest approach is to clear and let next refresh repopulate.
            # Here we fetch latest available from entities masjid id; not accessible directly, so we no-op if we lack data.
            # Integrations will reschedule on coordinator updates automatically; for immediate user feedback, we can attempt to rebuild from last known times stored on self.
            if hasattr(self, "_last_data") and self._last_data:
                self.schedule_from_data(self._last_data)

        # Store last_data when scheduling
        orig_schedule = self.schedule_from_data

        def _wrap_schedule(data: dict[str, Any]) -> None:
            self._last_data = data
            orig_schedule(data)

        self.schedule_from_data = _wrap_schedule  # type: ignore[assignment]

        self._handles.append(async_track_state_change_event(self.hass, targets, _reschedule))


