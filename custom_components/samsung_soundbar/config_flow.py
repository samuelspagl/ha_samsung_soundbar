"""Config flow for Samsung Soundbar."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import pysmartthings
import voluptuous as vol
from voluptuous import All, Range

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlowResult,
)
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_TOKEN,
)
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AUTH_MODE_OAUTH,
    AUTH_MODE_PAT,
    CONF_AUTH_MODE,
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

SMARTTHINGS_SCOPES = ["r:devices:*", "x:devices:*"]
SMARTTHINGS_DOMAIN = "smartthings"
SmartThings = pysmartthings.SmartThings


def _create_api_client(session, token: str):
    """Create a SmartThings client compatible with multiple pysmartthings versions."""
    try:
        return SmartThings(session=session, _token=token)
    except TypeError:
        # pysmartthings<3 uses SmartThings(session, token)
        return SmartThings(session, token)


async def _fetch_device(api, device_id: str):
    """Fetch device with compatibility across pysmartthings versions."""
    get_device = getattr(api, "get_device", None)
    if callable(get_device):
        return await get_device(device_id)
    legacy_device = getattr(api, "device", None)
    if callable(legacy_device):
        return await legacy_device(device_id)
    raise RuntimeError("Unsupported pysmartthings version: no device lookup method")


def _map_flow_error(excp: Exception) -> tuple[str | None, str]:
    """Map SmartThings exceptions to config flow errors."""
    exc_name = excp.__class__.__name__

    if exc_name in {"SmartThingsAuthenticationFailedError", "SmartThingsForbiddenError"}:
        return CONF_ENTRY_API_KEY, "invalid_auth"
    if exc_name in {"SmartThingsNotFoundError", "APINotFoundError"}:
        return CONF_ENTRY_DEVICE_ID, "device_not_found"
    if exc_name in {"SmartThingsConnectionError"}:
        return None, "cannot_connect"
    return None, "fetch_failed"


class SamsungSoundbarFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle Samsung Soundbar config flow."""

    DOMAIN = DOMAIN
    VERSION = 2

    def __init__(self) -> None:
        """Initialize flow."""
        super().__init__()
        self._pending_data: dict[str, Any] = {}
        self._reconfigure_entry: ConfigEntry | None = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {"scope": " ".join(SMARTTHINGS_SCOPES)}

    async def _async_validate_device(self, token: str, device_id: str):
        """Validate a SmartThings device with a bearer token."""
        api = _create_api_client(async_get_clientsession(self.hass), token)
        return await _fetch_device(api, device_id)

    async def _async_has_smartthings_implementation(self) -> bool:
        """Check if smartthings OAuth implementation is available."""
        implementations = await config_entry_oauth2_flow.async_get_implementations(
            self.hass, DOMAIN
        )
        return SMARTTHINGS_DOMAIN in implementations

    async def _async_import_smartthings_credentials(self) -> str:
        """Import reusable credentials from official SmartThings entries.

        Returns one of: imported, missing, import_failed.
        """
        smartthings_entries = self.hass.config_entries.async_entries(SMARTTHINGS_DOMAIN)
        for entry in smartthings_entries:
            client_id = entry.data.get(CONF_CLIENT_ID)
            client_secret = entry.data.get(CONF_CLIENT_SECRET)
            if not isinstance(client_id, str) or not client_id:
                continue
            if not isinstance(client_secret, str) or not client_secret:
                continue

            try:
                await async_import_client_credential(
                    self.hass,
                    DOMAIN,
                    ClientCredential(
                        client_id=client_id,
                        client_secret=client_secret,
                        name="Imported from SmartThings",
                    ),
                    auth_domain=SMARTTHINGS_DOMAIN,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Failed to import SmartThings OAuth credentials for %s",
                    DOMAIN,
                    exc_info=True,
                )
                return "import_failed"

            _LOGGER.debug("Imported SmartThings OAuth credentials for %s", DOMAIN)
            return "imported"

        _LOGGER.debug("No reusable SmartThings OAuth credentials found")
        return "missing"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "oauth"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle PAT setup."""
        errors: dict[str, str] = {}
        defaults = user_input or {}

        if user_input is not None:
            try:
                device = await self._async_validate_device(
                    user_input[CONF_ENTRY_API_KEY], user_input[CONF_ENTRY_DEVICE_ID]
                )
            except Exception as excp:  # noqa: BLE001
                field, message = _map_flow_error(excp)
                if field:
                    errors[field] = message
                else:
                    errors["base"] = message
            else:
                device_name = user_input[CONF_ENTRY_DEVICE_NAME] or (
                    device.label or device.name or user_input[CONF_ENTRY_DEVICE_ID]
                )
                self._pending_data = {
                    CONF_AUTH_MODE: AUTH_MODE_PAT,
                    CONF_ENTRY_API_KEY: user_input[CONF_ENTRY_API_KEY],
                    CONF_ENTRY_DEVICE_ID: user_input[CONF_ENTRY_DEVICE_ID],
                    CONF_ENTRY_DEVICE_NAME: device_name,
                    CONF_ENTRY_MAX_VOLUME: user_input[CONF_ENTRY_MAX_VOLUME],
                }
                return await self.async_step_device()

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_API_KEY,
                        default=defaults.get(CONF_ENTRY_API_KEY, ""),
                    ): str,
                    vol.Required(
                        CONF_ENTRY_DEVICE_ID,
                        default=defaults.get(CONF_ENTRY_DEVICE_ID, ""),
                    ): str,
                    vol.Required(
                        CONF_ENTRY_DEVICE_NAME,
                        default=defaults.get(CONF_ENTRY_DEVICE_NAME, ""),
                    ): str,
                    vol.Required(
                        CONF_ENTRY_MAX_VOLUME,
                        default=defaults.get(CONF_ENTRY_MAX_VOLUME, 100),
                    ): All(int, Range(min=1, max=100)),
                }
            ),
            errors=errors,
        )

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start OAuth setup."""
        if await self._async_has_smartthings_implementation():
            return await self.async_step_pick_implementation(
                user_input={"implementation": SMARTTHINGS_DOMAIN}
            )

        import_result = await self._async_import_smartthings_credentials()
        if import_result == "import_failed":
            return self.async_abort(reason="smartthings_oauth_import_failed")

        if await self._async_has_smartthings_implementation():
            return await self.async_step_pick_implementation(
                user_input={"implementation": SMARTTHINGS_DOMAIN}
            )

        return self.async_abort(reason="missing_smartthings_oauth_credentials")

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create an entry after OAuth flow."""
        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
            device_id = entry.data.get(CONF_ENTRY_DEVICE_ID)
            if isinstance(device_id, str):
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_mismatch(reason="reauth_account_mismatch")

            new_data = {**entry.data, **data, CONF_AUTH_MODE: AUTH_MODE_OAUTH}
            new_data.pop(CONF_ENTRY_API_KEY, None)
            return self.async_update_reload_and_abort(entry, data=new_data)

        if self._reconfigure_entry is not None:
            new_data = {
                **self._reconfigure_entry.data,
                **data,
                CONF_AUTH_MODE: AUTH_MODE_OAUTH,
            }
            new_data.pop(CONF_ENTRY_API_KEY, None)
            return self.async_update_reload_and_abort(
                self._reconfigure_entry,
                data=new_data,
                reason="reconfigure_successful",
            )

        self._pending_data = {**data, CONF_AUTH_MODE: AUTH_MODE_OAUTH}
        return await self.async_step_oauth_device()

    async def async_step_oauth_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect device data after OAuth."""
        errors: dict[str, str] = {}
        defaults = user_input or {}

        if user_input is not None:
            token_data = self._pending_data.get(CONF_TOKEN, {})
            access_token = token_data.get(CONF_ACCESS_TOKEN)
            if not isinstance(access_token, str) or not access_token:
                return self.async_abort(reason="oauth_token_invalid")

            try:
                device = await self._async_validate_device(
                    access_token, user_input[CONF_ENTRY_DEVICE_ID]
                )
            except Exception as excp:  # noqa: BLE001
                field, message = _map_flow_error(excp)
                if field:
                    errors[field] = message
                else:
                    errors["base"] = message
            else:
                device_name = user_input[CONF_ENTRY_DEVICE_NAME] or (
                    device.label or device.name or user_input[CONF_ENTRY_DEVICE_ID]
                )
                self._pending_data.update(
                    {
                        CONF_ENTRY_DEVICE_ID: user_input[CONF_ENTRY_DEVICE_ID],
                        CONF_ENTRY_DEVICE_NAME: device_name,
                        CONF_ENTRY_MAX_VOLUME: user_input[CONF_ENTRY_MAX_VOLUME],
                    }
                )
                return await self.async_step_device()

        return self.async_show_form(
            step_id="oauth_device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_DEVICE_ID,
                        default=defaults.get(CONF_ENTRY_DEVICE_ID, ""),
                    ): str,
                    vol.Required(
                        CONF_ENTRY_DEVICE_NAME,
                        default=defaults.get(CONF_ENTRY_DEVICE_NAME, ""),
                    ): str,
                    vol.Required(
                        CONF_ENTRY_MAX_VOLUME,
                        default=defaults.get(CONF_ENTRY_MAX_VOLUME, 100),
                    ): All(int, Range(min=1, max=100)),
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect optional feature settings and create entry."""
        if user_input is not None:
            entry_data = {**self._pending_data, **user_input}
            device_id = entry_data[CONF_ENTRY_DEVICE_ID]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=entry_data[CONF_ENTRY_DEVICE_NAME],
                data=entry_data,
            )

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES,
                        default=False,
                    ): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_EQ_SELECTOR, default=False): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
                        default=False,
                    ): bool,
                    vol.Required(CONF_ENTRY_SETTINGS_WOOFER_NUMBER, default=False): bool,
                }
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle integration reconfiguration."""
        self._reconfigure_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reconfigure_entry is None:
            return self.async_abort(reason="entry_not_found")

        auth_mode = self._reconfigure_entry.data.get(CONF_AUTH_MODE, AUTH_MODE_PAT)
        if auth_mode == AUTH_MODE_PAT:
            return self.async_show_menu(
                step_id="reconfigure",
                menu_options=["reconfigure_confirm", "reconfigure_oauth"],
            )
        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update device feature settings."""
        if self._reconfigure_entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._reconfigure_entry,
                data_updates=user_input,
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES,
                        default=self._reconfigure_entry.data.get(
                            CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, False
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_EQ_SELECTOR,
                        default=self._reconfigure_entry.data.get(
                            CONF_ENTRY_SETTINGS_EQ_SELECTOR, False
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
                        default=self._reconfigure_entry.data.get(
                            CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, False
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_SETTINGS_WOOFER_NUMBER,
                        default=self._reconfigure_entry.data.get(
                            CONF_ENTRY_SETTINGS_WOOFER_NUMBER, False
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ENTRY_MAX_VOLUME,
                        default=self._reconfigure_entry.data.get(
                            CONF_ENTRY_MAX_VOLUME, 100
                        ),
                    ): All(int, Range(min=1, max=100)),
                }
            ),
        )

    async def async_step_reconfigure_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Migrate PAT entry to OAuth through reconfigure."""
        if self._reconfigure_entry is None:
            return self.async_abort(reason="entry_not_found")
        return await self.async_step_oauth(user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication for OAuth entries."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication."""
        reauth_entry = self._get_reauth_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={"name": reauth_entry.title},
            )

        implementation = reauth_entry.data.get("auth_implementation")
        if not isinstance(implementation, str) or not implementation:
            return self.async_abort(reason="missing_auth_implementation")

        return await self.async_step_pick_implementation(
            user_input={"implementation": implementation}
        )
