"""Config flow for Samsung Soundbar integration (Manual Token)."""

from __future__ import annotations

import logging
from typing import Any

import pysmartthings
import voluptuous as vol
from aiohttp import ClientResponseError
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ENTRY_DEVICE_ID,
    CONF_ENTRY_DEVICE_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SamsungSoundbarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Samsung Soundbar config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._devices: dict[str, str] = {}
        self._token: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_ACCESS_TOKEN]

            try:
                api = pysmartthings.SmartThings(
                    session=async_get_clientsession(self.hass)
                )
                api.authenticate(token)

                devices = await api.get_devices()

                self._devices = {
                    device.device_id: getattr(device, "label", None)
                    or device.device_id
                    for device in devices
                }

                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    self._token = token
                    return await self.async_step_device()

            except (ClientResponseError, Exception) as exc:
                _LOGGER.error("SmartThings token validation failed: %s", exc)
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        if user_input is not None:

            await self.async_set_unique_id(
                user_input[CONF_ENTRY_DEVICE_ID]
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_ENTRY_DEVICE_NAME],
                data={
                    CONF_ACCESS_TOKEN: self._token,
                    CONF_ENTRY_DEVICE_ID: user_input[
                        CONF_ENTRY_DEVICE_ID
                    ],
                    CONF_ENTRY_DEVICE_NAME: user_input[
                        CONF_ENTRY_DEVICE_NAME
                    ],
                },
            )

        default_device_id = next(iter(self._devices), None)
        default_name = self._devices.get(default_device_id, DOMAIN)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_DEVICE_ID,
                        default=default_device_id,
                    ): vol.In(self._devices),
                    vol.Required(
                        CONF_ENTRY_DEVICE_NAME,
                        default=default_name,
                    ): str,
                }
            ),
        )
