"""Config flow for Samsung Soundbar integration."""

from __future__ import annotations

import logging
from typing import Any

import pysmartthings
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pysmartthings import APIResponseError
from voluptuous import All, Range

from .const import (
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

DEFAULT_OPTIONS = {
    CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES: False,
    CONF_ENTRY_SETTINGS_EQ_SELECTOR: False,
    CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR: False,
    CONF_ENTRY_SETTINGS_WOOFER_NUMBER: False,
    CONF_ENTRY_MAX_VOLUME: 100,
}


def _get_authenticated_client(hass, token: str) -> pysmartthings.SmartThings:
    api = pysmartthings.SmartThings(session=async_get_clientsession(hass))
    api.authenticate(token)
    return api


async def validate_input(api: pysmartthings.SmartThings, device_id: str):
    """Validate that the selected device exists and can be loaded."""
    try:
        return await api.get_device(device_id)
    except APIResponseError as exc:
        _LOGGER.error("[Samsung Soundbar] ERROR: %s", str(exc))
        raise ValueError from exc


class SamsungSoundbarFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a Samsung Soundbar OAuth2 config flow."""

    VERSION = 1

    reauth_entry: config_entries.ConfigEntry | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._oauth_data: dict[str, Any] | None = None
        self._available_devices: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return options flow for this handler."""
        return SamsungSoundbarOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Start OAuth flow."""
        return await super().async_step_user(user_input)

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create config entry after OAuth has completed."""
        self._oauth_data = data

        session = config_entry_oauth2_flow.OAuth2Session(self.hass, self.flow_impl, data)
        await session.async_ensure_token_valid()
        api = _get_authenticated_client(self.hass, session.token[CONF_ACCESS_TOKEN])

        try:
            devices = await api.get_devices()
        except Exception as exc:  # pragma: no cover - defensive for runtime API errors
            _LOGGER.error("Unable to fetch SmartThings devices during setup: %s", exc)
            return self.async_abort(reason="fetch_failed")

        self._available_devices = {
            device.device_id: getattr(device, "label", None) or device.device_id
            for device in devices
        }

        if self.reauth_entry:
            return self.async_update_reload_and_abort(
                self.reauth_entry,
                data={**self.reauth_entry.data, **data},
                reason="reauth_successful",
            )

        if not self._available_devices:
            return self.async_abort(reason="no_devices")

        return await self.async_step_device()

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Pick a SmartThings device and create entry."""
        if user_input is not None:
            assert self._oauth_data is not None

            session = config_entry_oauth2_flow.OAuth2Session(
                self.hass, self.flow_impl, self._oauth_data
            )
            await session.async_ensure_token_valid()
            api = _get_authenticated_client(self.hass, session.token[CONF_ACCESS_TOKEN])

            try:
                await validate_input(api, user_input[CONF_ENTRY_DEVICE_ID])
            except Exception:
                return self.async_abort(reason="fetch_failed")

            await self.async_set_unique_id(user_input[CONF_ENTRY_DEVICE_ID])
            self._abort_if_unique_id_configured()

            entry_data = {
                **self._oauth_data,
                CONF_ENTRY_DEVICE_ID: user_input[CONF_ENTRY_DEVICE_ID],
                CONF_ENTRY_DEVICE_NAME: user_input[CONF_ENTRY_DEVICE_NAME],
            }
            return self.async_create_entry(
                title=user_input[CONF_ENTRY_DEVICE_NAME],
                data=entry_data,
                options=DEFAULT_OPTIONS,
            )

        default_device_id = next(iter(self._available_devices), None)
        default_name = self._available_devices.get(default_device_id, DOMAIN)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_DEVICE_ID,
                        default=default_device_id,
                    ): vol.In(self._available_devices),
                    vol.Required(CONF_ENTRY_DEVICE_NAME, default=default_name): str,
                }
            ),
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth request."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauthentication and restart OAuth flow."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")

        return await self.async_step_user()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        self.config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reconfigure_confirm(user_input)

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user-controlled feature toggles/max volume updates."""
        assert self.config_entry

        if user_input is not None:
            return self.async_update_reload_and_abort(
                self.config_entry,
                options={**self.config_entry.options, **user_input},
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=_options_schema(self.config_entry.options),
        )


class SamsungSoundbarOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Samsung Soundbar options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={**self.config_entry.options, **user_input},
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry.options),
        )


def _options_schema(options: dict[str, Any]) -> vol.Schema:
    merged_options = {**DEFAULT_OPTIONS, **options}
    return vol.Schema(
        {
            vol.Required(
                CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES,
                default=merged_options[CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES],
            ): bool,
            vol.Required(
                CONF_ENTRY_SETTINGS_EQ_SELECTOR,
                default=merged_options[CONF_ENTRY_SETTINGS_EQ_SELECTOR],
            ): bool,
            vol.Required(
                CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
                default=merged_options[CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR],
            ): bool,
            vol.Required(
                CONF_ENTRY_SETTINGS_WOOFER_NUMBER,
                default=merged_options[CONF_ENTRY_SETTINGS_WOOFER_NUMBER],
            ): bool,
            vol.Required(
                CONF_ENTRY_MAX_VOLUME,
                default=merged_options[CONF_ENTRY_MAX_VOLUME],
            ): All(int, Range(min=1, max=100)),
        }
    )
