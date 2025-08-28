<div align="center">
  <img src="icon.svg" alt="The Masjid App" width="96" height="96">
  <h1>The Masjid App</h1>
  <p><em>Home Assistant custom integration</em></p>
</div>

Author

- name: "Sabaat Ahmad"
- email: "sabaatworld@gmail.com"

Overview

The Masjid App integration fetches prayer times from `themasjidapp.net/<masjid_id>` and automates:
- Azan playback at azan times, with per-prayer volume and optional pausing/resuming of other media players
- Pre-prayer actions: optional car start and water recirculation before each prayer
- Ramadan reminder (TTS) before Maghrib when Ramadan reminder is on

Key features

- UI-based configuration (no YAML)
- Optional features are completely skipped if not configured
- Prayer time polling interval (hours) with in-memory caching for fallback when the server is unreachable
- Entities named using a sanitized mosque name to ensure valid entity IDs
- Improved entity names for better clarity and user experience
- Consistent icon design for easy visual identification

Installation

1) Copy this folder `ha_the_masjid_app` into `config/custom_components/`.
2) Restart Home Assistant.
3) Go to Settings → Devices & Services → Add Integration → search for "The Masjid App".

Configuration (via UI)

- Required
  - Masjid ID: numeric ID (e.g., `41` means times at `http://themasjidapp.net/41`)
  - Fetch Interval (Hours): integer 1–12



- Optional (each skipped if left empty)
  - Media Player For Azan: `media_player.xxx`
  - Azan Media Content ID: media-source or URL (e.g., `media-source://media_source/local/Prayers/azan.mp3`)
  - Azan Media Length (Seconds): used to restore volume and resume other players after playback
  - Players To Pause During Azan: select multiple `media_player` entities
  - Water Recirculation Service: `domain.service` (e.g., `script.start_garage_water_pump`)
  - Water Recirculation Params: comma-separated `key=value` pairs (e.g., `entity_id=switch.pump,duration=60`)
  - Car Start Service: `domain.service` (e.g., `ad_drone.start_car`)
  - Car Start Params: comma-separated `key=value` pairs (e.g., `auto_stop_mins=4`)
  - Presence Sensors: select multiple sensors (binary sensors, device trackers, person entities) - only runs car/pump actions when ALL selected sensors indicate presence
  - TTS Entity For Ramadan Reminder: used for Ramadan reminder (e.g., `tts.piper`)

Entities

All entity IDs begin with a sanitized slug based on your mosque name to avoid invalid characters.

- Switches
  - `<mosque>_azan_enabled`: Turn azan playback on/off
  - `<mosque>_ramadan_reminder`: Enable Ramadan reminder behavior
  - `<mosque>_car_start_enabled`: Enable car-start automation
  - `<mosque>_water_recirc_enabled`: Enable water recirculation automation

- Numbers
  - `<mosque>_<prayer>_azan_volume`: One per prayer (Fajr/Dhuhr/Asr/Maghrib/Isha), 0–100, step 5, default 50%
  - `<mosque>_car_start_minutes`: Default 10, 0–30, step 1
  - `<mosque>_water_recirc_minutes`: Default 15, 0–30, step 1
  - `<mosque>_ramadan_reminder_minutes`: Default 2, 0–30, step 1

- Time Entities (Read-only)
  - `<prayer>_azan`: Prayer azan times (Fajr/Dhuhr/Asr/Maghrib/Isha)
  - `<prayer>_iqama`: Prayer iqama times (Fajr/Dhuhr/Asr/Maghrib/Isha)

- Diagnostic Sensors
  - `last_fetch_time`: Timestamp of last successful data fetch
  - `last_cache_time`: Timestamp of last successful data cache update

- Configuration Entities (Device Configuration)
  - **Configuration Sensors**:
    - `masjid_id`: Masjid ID from configuration
    - `refresh_interval_hours`: Fetch interval from configuration
    - `media_player`: Media player entity ID from configuration
    - `media_content_id`: Media content ID from configuration
    - `media_content_length`: Media content length from configuration
    - `media_players_to_pause`: Media players to pause from configuration
    - `action_water_recirculation`: Water recirculation action from configuration
    - `action_water_recirculation_params`: Water recirculation parameters from configuration (JSON object)
    - `action_car_start`: Car start action from configuration
    - `action_car_start_params`: Car start parameters from configuration (JSON object)
    - `presence_sensors`: List of presence sensors from configuration
    - `tts_entity`: TTS entity from configuration
  - **Configuration Numbers**:
    - `<prayer>_azan_volume`: Azan volume controls for each prayer
    - `car_start`: Car start timer (minutes)
    - `water_recirculation`: Water recirculation timer (minutes)
    - `ramadan_reminder`: Ramadan reminder timer (minutes)
  - **Configuration Switches**:
    - `azan`: Azan feature toggle
    - `ramadan_reminder`: Ramadan reminder toggle
    - `car_start`: Car start feature toggle
    - `water_recirculation`: Water recirculation feature toggle

Behavior and scheduling

- Data fetching
  - Polls `http://themasjidapp.net/<masjid_id>` on the configured interval.
  - Caches the latest successful JSON and uses it on fetch failures.

- Scheduling
  - Azan plays at azan time (requires media player + content ID). Sets per-prayer volume, pauses listed players during playback, restores volume and resumes after `length + 3s`.
  - Car start runs at prayer time minus `<mosque>_car_start_minutes` (requires car service; presence is respected if configured).
  - Water recirculation runs at prayer time minus `<mosque>_water_recirc_minutes` (requires water service; presence is respected if configured).
  - Ramadan reminder runs at Maghrib time minus `<mosque>_ramadan_reminder_minutes` (requires TTS entity and Ramadan reminder switch ON).
  - Schedule automatically refreshes when new prayer times are fetched and when the minute-offset numbers change.

Entity naming and slugging

- The mosque name from server is sanitized to a lowercase slug with only `[a-z0-9_]` to ensure valid entity IDs.

Entity icons and visual design

- All entities include appropriate Material Design Icons (MDI) for better visual identification:
  - Azan entities: volume-high icon
  - Car-related entities: car icon (switches) and timer icon (time settings)
  - Water recirculation: water-pump icon (switches) and timer icon (time settings)
  - Ramadan reminder: bell-plus icon (switches) and timer icon (time settings)
  - Prayer time entities: clock icon (time entities)
  - Diagnostic entities: information icon (diagnostic sensors)
  - Configuration entities: settings/volume/timer/car/water icons (configuration sensors, numbers, switches)

Advanced notes

- Action parameter format: parameters are provided as JSON objects and passed directly as service data.
- If azan media player or content ID are not provided, azan playback is skipped entirely.
- If presence sensor is provided and is `off`, car/water actions are skipped.
- The integration creates time, sensor, number, and switch entities.
- Time entities are read-only and display prayer times in a user-friendly format.
- Diagnostic sensors provide information about data fetching and caching status.
- Configuration entities (sensors, numbers, switches) are grouped in the device configuration section using EntityCategory.CONFIG.
- Only last fetch and last cache time sensors are diagnostic entities using EntityCategory.DIAGNOSTIC.
- All entities are grouped under a device named after the mosque name from the configuration.
- The device includes all entity types: time, sensor, number, and switch entities.

Uninstall

- Remove the integration from Settings → Devices & Services, then delete the folder from `custom_components` if desired.

Support

- Author: "Sabaat Ahmad" <sabaatworld@gmail.com>
- This project was translated from an AppDaemon script to a native Home Assistant integration.

Attribution and icon

- A simple mosque-themed SVG icon is included as `icon.svg` in this directory for branding in documentation and stores.


