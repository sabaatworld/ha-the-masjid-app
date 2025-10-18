from __future__ import annotations

from typing import Final

DOMAIN: Final[str] = "ha_the_masjid_app"

CONF_DEVICE_ID: Final[str] = "device_id"
CONF_MASJID_ID: Final[str] = "masjid_id"
CONF_MASJID_NAME: Final[str] = "masjid_name"
CONF_REFRESH_INTERVAL_HOURS: Final[str] = "refresh_interval_hours"
CONF_MEDIA_PLAYER: Final[str] = "media_player"
CONF_MEDIA_DATA: Final[str] = "media_data"
CONF_MEDIA_CONTENT_LENGTH: Final[str] = "media_content_length"
CONF_MEDIA_PLAYERS_TO_PAUSE: Final[str] = "media_players_to_pause"
CONF_ACTION_WATER_RECIRCULATION: Final[str] = "action_water_recirculation"
CONF_ACTION_CAR_START: Final[str] = "action_car_start"
CONF_ACTION_WATER_RECIRCULATION_PARAMS: Final[str] = "action_water_recirculation_params"
CONF_ACTION_CAR_START_PARAMS: Final[str] = "action_car_start_params"
CONF_PRESENCE_SENSORS: Final[str] = "presence_sensors"
CONF_TTS_ENTITY: Final[str] = "tts_entity"

# Entity settings that need to be persisted
CONF_AZAN_ENABLED: Final[str] = "azan_enabled"
CONF_RAMADAN_REMINDER_ENABLED: Final[str] = "ramadan_reminder_enabled"
CONF_CAR_START_ENABLED: Final[str] = "car_start_enabled"
CONF_WATER_RECIRC_ENABLED: Final[str] = "water_recirc_enabled"
CONF_CAR_START_MINUTES: Final[str] = "car_start_minutes"
CONF_WATER_RECIRC_MINUTES: Final[str] = "water_recirc_minutes"
CONF_RAMADAN_REMINDER_MINUTES: Final[str] = "ramadan_reminder_minutes"

# Azan volume base constant
CONF_AZAN_VOLUME_BASE: Final[str] = "azan_volume"

# Azan volume settings for each prayer
CONF_AZAN_VOLUME_FAJR: Final[str] = f"{CONF_AZAN_VOLUME_BASE}_fajr"
CONF_AZAN_VOLUME_DHUHR: Final[str] = f"{CONF_AZAN_VOLUME_BASE}_dhuhr"
CONF_AZAN_VOLUME_ASR: Final[str] = f"{CONF_AZAN_VOLUME_BASE}_asr"
CONF_AZAN_VOLUME_MAGHRIB: Final[str] = f"{CONF_AZAN_VOLUME_BASE}_maghrib"
CONF_AZAN_VOLUME_ISHA: Final[str] = f"{CONF_AZAN_VOLUME_BASE}_isha"

# Test azan settings
CONF_AZAN_VOLUME_TEST: Final[str] = f"{CONF_AZAN_VOLUME_BASE}_test"

DEFAULT_REFRESH_INTERVAL_HOURS: Final[int] = 6
AZAN_VOLUME_DEFAULT: Final[int] = 50

VOLUME_STEPS: Final[int] = 5
VOLUME_MIN: Final[int] = 0
VOLUME_MAX: Final[int] = 100

CAR_START_MINUTES_DEFAULT: Final[int] = 10
WATER_RECIRC_MINUTES_DEFAULT: Final[int] = 15
RAMADAN_REMINDER_MINUTES_DEFAULT: Final[int] = 2

CAR_WATER_MINUTES_MIN: Final[int] = 0
CAR_WATER_MINUTES_MAX: Final[int] = 30
RAMADAN_REMINDER_MIN: Final[int] = 1
RAMADAN_REMINDER_MAX: Final[int] = 30

PRAYERS: list[str] = ["fajr", "dhuhr", "asr", "maghrib", "isha", "test"]

# Map prayer names to JSON response keys.
AZAN_NAME_MAP: dict[str, str] = {"fajr": "fajr", "dhuhr": "zuhr", "asr": "asr", "maghrib": "maghrib", "isha": "isha", "test": "test"}

# Entity Registry Keys
ENTITY_KEY_CAR_START_MINUTES: Final[str] = f"number_{CONF_CAR_START_MINUTES}"
ENTITY_KEY_WATER_RECIRC_MINUTES: Final[str] = f"number_{CONF_WATER_RECIRC_MINUTES}"
ENTITY_KEY_RAMADAN_REMINDER_MINUTES: Final[str] = f"number_{CONF_RAMADAN_REMINDER_MINUTES}"
ENTITY_KEY_AZAN_VOLUME_BASE: Final[str] = f"number_{CONF_AZAN_VOLUME_BASE}"

ENTITY_KEY_AZAN_ENABLED: Final[str] = f"switch_{CONF_AZAN_ENABLED}"
ENTITY_KEY_CAR_START_ENABLED: Final[str] = f"switch_{CONF_CAR_START_ENABLED}"
ENTITY_KEY_WATER_RECIRC_ENABLED: Final[str] = f"switch_{CONF_WATER_RECIRC_ENABLED}"
ENTITY_KEY_RAMADAN_REMINDER_ENABLED: Final[str] = f"switch_{CONF_RAMADAN_REMINDER_ENABLED}"

ENTITY_KEY_LAST_FETCH_TIME: Final[str] = "sensor_last_fetch_time"
ENTITY_KEY_LAST_CACHE_TIME: Final[str] = "sensor_last_cache_time"
ENTITY_KEY_PRAYER_TIME_BASE: Final[str] = "sensor_prayer_time"

ENTITY_KEY_FORCE_REFRESH: Final[str] = "button_force_refresh"
ENTITY_KEY_TEST_AZAN: Final[str] = "button_test_azan"
ENTITY_KEY_TEST_AZAN_SCHEDULE: Final[str] = "button_test_azan_schedule"
ENTITY_KEY_TEST_PRAYER_SCHEDULE: Final[str] = "button_test_prayer_schedule"
