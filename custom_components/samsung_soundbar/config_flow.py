import logging
from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol
from homeassistant import config_entries
from voluptuous import All, Range

from .smartthings_api import SmartThingsApi
from .const import (
    CONF_ENTRY_API_KEY,
    CONF_ENTRY_DEVICE_ID,
    CONF_ENTRY_DEVICE_NAME,
    CONF_ENTRY_MAX_VOLUME,
    CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES,
    CONF_ENTRY_SETTINGS_EQ_SELECTOR,
    CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
    CONF_ENTRY_SETTINGS_WOOFER_NUMBER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass, token: str, device_id: str) -> dict[str, Any]:
    api = SmartThingsApi(hass, token)
    return await api.get_device(device_id)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.user_input = user_input
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENTRY_API_KEY): str,
                    vol.Required(CONF_ENTRY_DEVICE_ID): str,
                    vol.Required(CONF_ENTRY_DEVICE_NAME): str,
                    vol.Required(CONF_ENTRY_MAX_VOLUME, default=100): All(
                        int, Range(min=1, max=100)
                    ),
                }
            ),
        )

    async def async_step_device(self, user_input: dict[str, Any] | None = None):
        # `fetch_failed` in the UI is often caused by exceptions inside the flow.
        # Be defensive: flows can be resumed and `self.user_input` might not exist.
        if not hasattr(self, "user_input") or self.user_input is None:
            self.user_input = {}

        if user_input is not None:
            self.user_input.update(user_input)

            try:
                device = await validate_input(
                    self.hass,
                    self.user_input.get(CONF_ENTRY_API_KEY),
                    self.user_input.get(CONF_ENTRY_DEVICE_ID),
                )
                _LOGGER.debug(
                    f"Successfully validated Input, Creating entry with title {DOMAIN} and data {user_input}"
                )
            except ClientResponseError as excp:
                _LOGGER.exception("Config flow validation failed (HTTP %s)", excp.status)
                if excp.status == 401:
                    base_error = "invalid_auth"
                elif excp.status == 404:
                    base_error = "invalid_device"
                else:
                    base_error = "cannot_connect"
                # Keep the user on the same step with a useful base error.
                return self.async_show_form(
                    step_id="device",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, default=self.user_input.get(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, False)): bool,
                            vol.Required(CONF_ENTRY_SETTINGS_EQ_SELECTOR, default=self.user_input.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR, False)): bool,
                            vol.Required(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, default=self.user_input.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, False)): bool,
                            vol.Required(CONF_ENTRY_SETTINGS_WOOFER_NUMBER, default=self.user_input.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER, False)): bool,
                        }
                    ),
                    errors={"base": base_error},
                )
            except Exception:
                _LOGGER.exception("Config flow validation failed")
                return self.async_show_form(
                    step_id="device",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, default=self.user_input.get(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, False)): bool,
                            vol.Required(CONF_ENTRY_SETTINGS_EQ_SELECTOR, default=self.user_input.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR, False)): bool,
                            vol.Required(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, default=self.user_input.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, False)): bool,
                            vol.Required(CONF_ENTRY_SETTINGS_WOOFER_NUMBER, default=self.user_input.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER, False)): bool,
                        }
                    ),
                    errors={"base": "cannot_connect"},
                )
            # Use the device label/name as the entry title if possible (nicer UI).
            title = None
            if isinstance(device, dict):
                title = device.get("label") or device.get("name")
            return self.async_create_entry(title=title or DOMAIN, data=self.user_input)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, default=False): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_EQ_SELECTOR, default=False): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, default=False): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_WOOFER_NUMBER, default=False): bool,
                }
            ),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle a reconfiguration flow initialized by the user."""
        self.config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle a reconfiguration flow initialized by the user."""
        errors: dict[str, str] = {}
        assert self.config_entry

        if user_input is not None:
            return self.async_update_reload_and_abort(
                self.config_entry,
                data={**self.config_entry.data, **user_input},
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES,
                        default=self.config_entry.data.get(
                            CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_EQ_SELECTOR,
                        default=self.config_entry.data.get(
                            CONF_ENTRY_SETTINGS_EQ_SELECTOR
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
                        default=self.config_entry.data.get(
                            CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_WOOFER_NUMBER,
                        default=self.config_entry.data.get(
                            CONF_ENTRY_SETTINGS_WOOFER_NUMBER
                        ),
                    ): bool,
                    vol.Required(CONF_ENTRY_MAX_VOLUME, default=100): All(
                        int, Range(min=1, max=100)
                    ),
                }
            ),
            errors=errors,
        )
