import logging
from typing import Any

import pysmartthings
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pysmartthings import APIResponseError
from voluptuous import All, Range

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


async def validate_input(api, device_id: str):
    try:
        return await api.device(device_id)
    except APIResponseError as excp:
        _LOGGER.error("[Samsung Soundbar] ERROR: %s", str(excp))
        raise ValueError


class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
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

    async def async_step_device(self, user_input: dict[str, any] | None = None):
        if user_input is not None:
            self.user_input.update(user_input)

            try:
                session = async_get_clientsession(self.hass)
                api = pysmartthings.SmartThings(
                    session, self.user_input.get(CONF_ENTRY_API_KEY)
                )
                device = await validate_input(
                    api, self.user_input.get(CONF_ENTRY_DEVICE_ID)
                )
                _LOGGER.debug(
                    f"Successfully validated Input, Creating entry with title {DOMAIN} and data {user_input}"
                )
            except Exception as excp:
                _LOGGER.error(f"The ConfigFlow triggered an exception {excp}")
                return self.async_abort(reason="fetch_failed")
            return self.async_create_entry(title=DOMAIN, data=self.user_input)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_EQ_SELECTOR): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_WOOFER_NUMBER): bool,
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
