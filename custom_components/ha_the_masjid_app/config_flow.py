from __future__ import annotations

from typing import Any
import uuid
import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    ObjectSelector,
    ObjectSelectorConfig,
    MediaSelector,
    MediaSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_MASJID_ID,
    CONF_MASJID_NAME,
    CONF_PRAYER_TIME_PROVIDER,
    CONF_MADINA_APPS_CLIENT_ID,
    CONF_REFRESH_INTERVAL_HOURS,
    CONF_MEDIA_PLAYER,
    CONF_MEDIA_DATA,
    CONF_MEDIA_CONTENT_LENGTH,
    CONF_MEDIA_PLAYERS_TO_PAUSE,
    CONF_ACTION_WATER_RECIRCULATION,
    CONF_ACTION_CAR_START,
    CONF_ACTION_WATER_RECIRCULATION_PARAMS,
    CONF_ACTION_CAR_START_PARAMS,
    CONF_PRESENCE_SENSORS,
    CONF_TTS_ENTITY,
    PRAYER_TIME_PROVIDER_THEMASJIDAPP,
    PRAYER_TIME_PROVIDER_MADINAAPP,
)
# Import safe_slug for use in coordinator

_LOGGER = logging.getLogger(__name__)


class OptionalEntitySelector(EntitySelector):
    """Custom EntitySelector that allows empty selection for single entities."""

    def __call__(self, data):
        """Validate the entity selector input."""
        # Allow empty/None values for single entity selectors (multiple=False)
        if not self.config.get("multiple", False):
            if data in ("", None):
                return ""  # Return empty string for no selection

        # For multiple=True or non-empty values, use standard validation
        return super().__call__(data)


class OptionalMediaSelector(MediaSelector):
    """Custom MediaSelector that allows empty selection."""

    def __call__(self, data):
        """Validate the media selector input."""
        # Allow empty/None values
        if data in ("", None, {}):
            return {}  # Return empty dict for no selection

        # For non-empty values, use standard validation
        return super().__call__(data)


class ServiceSelector(SelectSelector):
    """Custom ServiceSelector that lists available Home Assistant services."""

    def __init__(self, hass):
        """Initialize the ServiceSelector with Home Assistant instance."""
        self._hass = hass

        # Get all available services and create options
        options = []

        if hass:
            all_services = hass.services.async_services()
            for domain, services in sorted(all_services.items()):
                for service_name in sorted(services.keys()):
                    service_id = f"{domain}.{service_name}"
                    options.append({"value": service_id, "label": service_id})

        # Initialize parent with dropdown configuration
        config = SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN
        )
        super().__init__(config)

    def __call__(self, data):
        """Validate the service selector input."""
        # Allow empty/None values since field is optional
        if data in ("", None):
            return ""  # Return empty string for no selection

        # For non-empty values, use standard validation
        return super().__call__(data)


class MasjidAppConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    # Centralized default values for both user and reconfigure flows
    _DEFAULTS = {
        CONF_REFRESH_INTERVAL_HOURS: 6,
        CONF_MEDIA_CONTENT_LENGTH: 60,
        CONF_MEDIA_PLAYER: "",
        CONF_MEDIA_DATA: {},
        CONF_MEDIA_PLAYERS_TO_PAUSE: [],
        CONF_ACTION_WATER_RECIRCULATION: "",
        CONF_ACTION_WATER_RECIRCULATION_PARAMS: {},
        CONF_ACTION_CAR_START: "",
        CONF_ACTION_CAR_START_PARAMS: {},
        CONF_PRESENCE_SENSORS: [],
        CONF_TTS_ENTITY: "",
    }

    def _get_default(self, key: str) -> Any:
        """Get default value for a configuration key."""
        return self._DEFAULTS.get(key, "")

    @staticmethod
    def _normalize_masjid_id(masjid_id: str) -> str:
        """Normalize masjid ID for comparisons and unique IDs."""
        return masjid_id.strip().lower()

    def _build_unique_id(self, provider: str, masjid_id: str) -> str:
        """Build a unique ID using provider prefix and masjid ID."""
        normalized_masjid_id = self._normalize_masjid_id(masjid_id)
        return f"{DOMAIN}_{provider}_{normalized_masjid_id}"

    async def _async_validate_masjid_id(
        self,
        provider: str,
        masjid_id: str,
    ) -> tuple[str | None, int | None, str | None]:
        """Validate masjid ID by fetching data from server.

        Returns:
            Tuple of (masjid_name, madina_apps_client_id, error_key)
            If successful: (masjid_name, madina_apps_client_id, None)
            If error: (None, None, error_key)
        """
        if provider == PRAYER_TIME_PROVIDER_THEMASJIDAPP:
            url = f"http://themasjidapp.net/{masjid_id}"
        elif provider == PRAYER_TIME_PROVIDER_MADINAAPP:
            url = f"https://services.madinaapps.com/kiosk-rest/clients/{masjid_id}/settingsbyalias"
        else:
            return None, None, "invalid_provider"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.warning(
                            "HTTP %d when validating provider '%s' masjid ID '%s'",
                            resp.status,
                            provider,
                            masjid_id,
                        )
                        return None, None, "invalid_masjid_id"

                    data = await resp.json()

                    if provider == PRAYER_TIME_PROVIDER_THEMASJIDAPP:
                        # Extract masjid name from themasjidapp response
                        masjid_data = data.get("masjid", {})
                        masjid_name = masjid_data.get("name")

                        if not masjid_name:
                            _LOGGER.warning(
                                "No masjid name found in themasjidapp response for ID '%s'",
                                masjid_id,
                            )
                            return None, None, "invalid_masjid_id"

                        return masjid_name, None, None

                    # Extract masjid name and client ID from Madina Apps response
                    masjid_name = data.get("clientName")
                    madina_apps_client_id = data.get("clientId")

                    if not masjid_name or madina_apps_client_id is None:
                        _LOGGER.warning(
                            "Missing clientName/clientId in Madina Apps response for alias '%s'",
                            masjid_id,
                        )
                        return None, None, "invalid_masjid_id"

                    return masjid_name, int(madina_apps_client_id), None

        except aiohttp.ClientError as err:
            _LOGGER.error(
                "Connection error validating provider '%s' masjid ID '%s': %s",
                provider,
                masjid_id,
                err,
            )
            return None, None, "cannot_connect"
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception(
                "Unexpected error validating provider '%s' masjid ID '%s': %s",
                provider,
                masjid_id,
                err,
            )
            return None, None, "unknown"

    def _get_user_schema(self) -> vol.Schema:
        """Get schema for user setup flow."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_PRAYER_TIME_PROVIDER,
                    default=PRAYER_TIME_PROVIDER_THEMASJIDAPP,
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {
                                "value": PRAYER_TIME_PROVIDER_THEMASJIDAPP,
                                "label": "The Masjid App",
                            },
                            {
                                "value": PRAYER_TIME_PROVIDER_MADINAAPP,
                                "label": "Madina Apps",
                            },
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_MASJID_ID): vol.All(
                    vol.Coerce(str),
                    vol.Length(min=1, max=50),
                ),
                vol.Required(CONF_REFRESH_INTERVAL_HOURS, default=self._get_default(CONF_REFRESH_INTERVAL_HOURS)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=12)
                ),
                vol.Optional(CONF_MEDIA_PLAYER, default=self._get_default(CONF_MEDIA_PLAYER)): OptionalEntitySelector(
                    EntitySelectorConfig(domain="media_player", multiple=False)
                ),
                vol.Optional(CONF_MEDIA_DATA, default=self._get_default(CONF_MEDIA_DATA)): OptionalMediaSelector(
                    MediaSelectorConfig(accept=["audio/*"])
                ),
                vol.Optional(CONF_MEDIA_CONTENT_LENGTH, default=self._get_default(CONF_MEDIA_CONTENT_LENGTH)): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
                vol.Optional(CONF_MEDIA_PLAYERS_TO_PAUSE, default=self._get_default(CONF_MEDIA_PLAYERS_TO_PAUSE)): EntitySelector(
                    EntitySelectorConfig(domain="media_player", multiple=True)
                ),
                vol.Optional(CONF_ACTION_WATER_RECIRCULATION, default=self._get_default(CONF_ACTION_WATER_RECIRCULATION)): ServiceSelector(self.hass),
                vol.Optional(CONF_ACTION_WATER_RECIRCULATION_PARAMS, default=self._get_default(CONF_ACTION_WATER_RECIRCULATION_PARAMS)): ObjectSelector(
                    ObjectSelectorConfig()
                ),
                vol.Optional(CONF_ACTION_CAR_START, default=self._get_default(CONF_ACTION_CAR_START)): ServiceSelector(self.hass),
                vol.Optional(CONF_ACTION_CAR_START_PARAMS, default=self._get_default(CONF_ACTION_CAR_START_PARAMS)): ObjectSelector(
                    ObjectSelectorConfig()
                ),
                vol.Optional(CONF_PRESENCE_SENSORS, default=self._get_default(CONF_PRESENCE_SENSORS)): EntitySelector(
                    EntitySelectorConfig(domain=["binary_sensor", "device_tracker", "person"], multiple=True)
                ),
                vol.Optional(CONF_TTS_ENTITY, default=self._get_default(CONF_TTS_ENTITY)): OptionalEntitySelector(
                    EntitySelectorConfig(domain="tts", multiple=False)
                ),
            }
        )

    def _get_reconfigure_schema(self) -> vol.Schema:
        """Get base schema for reconfigure flow."""
        return vol.Schema(
            {
                vol.Required(CONF_REFRESH_INTERVAL_HOURS, default=self._get_default(CONF_REFRESH_INTERVAL_HOURS)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=12)
                ),
                vol.Optional(CONF_MEDIA_PLAYER, default=self._get_default(CONF_MEDIA_PLAYER)): OptionalEntitySelector(
                    EntitySelectorConfig(domain="media_player", multiple=False)
                ),
                vol.Optional(CONF_MEDIA_DATA, default=self._get_default(CONF_MEDIA_DATA)): OptionalMediaSelector(
                    MediaSelectorConfig(accept=["audio/*"])
                ),
                vol.Optional(CONF_MEDIA_CONTENT_LENGTH, default=self._get_default(CONF_MEDIA_CONTENT_LENGTH)): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
                vol.Optional(CONF_MEDIA_PLAYERS_TO_PAUSE, default=self._get_default(CONF_MEDIA_PLAYERS_TO_PAUSE)): EntitySelector(
                    EntitySelectorConfig(domain="media_player", multiple=True)
                ),
                vol.Optional(CONF_ACTION_WATER_RECIRCULATION, default=self._get_default(CONF_ACTION_WATER_RECIRCULATION)): ServiceSelector(self.hass),
                vol.Optional(CONF_ACTION_WATER_RECIRCULATION_PARAMS, default=self._get_default(CONF_ACTION_WATER_RECIRCULATION_PARAMS)): ObjectSelector(
                    ObjectSelectorConfig()
                ),
                vol.Optional(CONF_ACTION_CAR_START, default=self._get_default(CONF_ACTION_CAR_START)): ServiceSelector(self.hass),
                vol.Optional(CONF_ACTION_CAR_START_PARAMS, default=self._get_default(CONF_ACTION_CAR_START_PARAMS)): ObjectSelector(
                    ObjectSelectorConfig()
                ),
                vol.Optional(CONF_PRESENCE_SENSORS, default=self._get_default(CONF_PRESENCE_SENSORS)): EntitySelector(
                    EntitySelectorConfig(domain=["binary_sensor", "device_tracker", "person"], multiple=True)
                ),
                vol.Optional(CONF_TTS_ENTITY, default=self._get_default(CONF_TTS_ENTITY)): OptionalEntitySelector(
                    EntitySelectorConfig(domain="tts", multiple=False)
                ),
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = user_input[CONF_PRAYER_TIME_PROVIDER]
            masjid_id = str(user_input[CONF_MASJID_ID]).strip()

            if not masjid_id:
                errors["base"] = "invalid_masjid_id"
                return self.async_show_form(step_id="user", data_schema=self._get_user_schema(), errors=errors)

            # Keep a sanitized value in options
            user_input[CONF_MASJID_ID] = masjid_id

            # Validate masjid ID by making API request
            masjid_name, madina_apps_client_id, error_key = await self._async_validate_masjid_id(provider, masjid_id)

            if error_key:
                errors["base"] = error_key
            else:
                # Use masjid name as title
                title = masjid_name

                await self.async_set_unique_id(self._build_unique_id(provider, masjid_id))
                self._abort_if_unique_id_configured()

                # Generate a persistent device ID that won't change across reloads or option changes
                device_id = str(uuid.uuid4())

                entry_data: dict[str, Any] = {
                    CONF_DEVICE_ID: device_id,
                    CONF_MASJID_NAME: masjid_name,
                    CONF_PRAYER_TIME_PROVIDER: provider,
                }

                if provider == PRAYER_TIME_PROVIDER_MADINAAPP and madina_apps_client_id is not None:
                    entry_data[CONF_MADINA_APPS_CLIENT_ID] = madina_apps_client_id

                return self.async_create_entry(
                    title=title,
                    data=entry_data,
                    options=user_input,
                )

        return self.async_show_form(step_id="user", data_schema=self._get_user_schema(), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle reconfiguration of the integration."""
        config_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        current_data = config_entry.data
        current_options = config_entry.options

        if user_input is not None:
            # Merge user_input on top of current_options
            merged_options = {**current_options, **user_input}
            _LOGGER.info("Reconfigure step - Merged options: %s", merged_options)

            return self.async_update_reload_and_abort(
                config_entry,
                data=current_data,
                options=merged_options,
            )

        # Create schema with suggested values
        schema_with_values = self.add_suggested_values_to_schema(
            self._get_reconfigure_schema(), current_options
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema_with_values,
            errors=errors
        )
