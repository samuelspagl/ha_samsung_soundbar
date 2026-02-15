"""The Samsung Soundbar integration."""

from __future__ import annotations

import logging

from aiohttp import ClientError
import pysmartthings

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .api_extension.SoundbarDevice import SoundbarDevice
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
from .models import SoundbarRuntimeData

_LOGGER = logging.getLogger(__name__)
SmartThings = pysmartthings.SmartThings

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SWITCH,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


def _create_api_client(
    session,
    token: str,
    refresh_token_function=None,
) -> SmartThings:
    """Create a SmartThings client compatible with multiple pysmartthings versions."""
    try:
        api: SmartThings = SmartThings(session=session, _token=token)
    except TypeError:
        # pysmartthings<3 uses SmartThings(session, token)
        api = SmartThings(session, token)

    if refresh_token_function is not None and hasattr(api, "refresh_token_function"):
        api.refresh_token_function = refresh_token_function
    return api


async def _fetch_device(api: SmartThings, device_id: str):
    """Fetch device with compatibility across pysmartthings versions."""
    get_device = getattr(api, "get_device", None)
    if callable(get_device):
        return await get_device(device_id)
    legacy_device = getattr(api, "device", None)
    if callable(legacy_device):
        return await legacy_device(device_id)
    raise ConfigEntryError("Unsupported pysmartthings version: no device lookup method")


def _is_auth_error(excp: Exception) -> bool:
    """Check if an exception indicates authentication failure."""
    return excp.__class__.__name__ in {
        "SmartThingsAuthenticationFailedError",
        "SmartThingsForbiddenError",
    }


def _is_not_found_error(excp: Exception) -> bool:
    """Check if an exception indicates missing device."""
    return excp.__class__.__name__ in {"SmartThingsNotFoundError", "APINotFoundError"}


def _is_connection_error(excp: Exception) -> bool:
    """Check if an exception indicates temporary connection issue."""
    return excp.__class__.__name__ in {"SmartThingsConnectionError"}


def _is_smartthings_error(excp: Exception) -> bool:
    """Check if an exception is a SmartThings library error."""
    return excp.__class__.__name__.startswith("SmartThings")


def _infer_auth_mode(entry: ConfigEntry) -> str:
    """Infer auth mode for legacy entries that don't have one yet."""
    if CONF_ENTRY_API_KEY in entry.data:
        return AUTH_MODE_PAT
    return AUTH_MODE_OAUTH


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entries to include explicit auth mode."""
    if CONF_AUTH_MODE in entry.data:
        return True

    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_AUTH_MODE: _infer_auth_mode(entry)},
    )
    _LOGGER.debug("[%s] Migrated config entry %s to include auth mode", DOMAIN, entry.entry_id)
    return True


async def _build_api_for_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> tuple[SmartThings, OAuth2Session | None]:
    """Build a SmartThings API client for a config entry."""
    auth_mode = entry.data.get(CONF_AUTH_MODE, _infer_auth_mode(entry))
    session = async_get_clientsession(hass)

    if auth_mode == AUTH_MODE_OAUTH:
        try:
            implementation = await async_get_config_entry_implementation(hass, entry)
        except ValueError as err:
            raise ConfigEntryAuthFailed("Missing OAuth implementation") from err
        oauth_session = OAuth2Session(hass, entry, implementation)
        try:
            await oauth_session.async_ensure_token_valid()
        except ClientError as err:
            raise ConfigEntryNotReady from err

        try:
            access_token = oauth_session.token.get(CONF_ACCESS_TOKEN)
        except KeyError as err:
            raise ConfigEntryAuthFailed("Missing OAuth token payload") from err
        if not isinstance(access_token, str) or not access_token:
            raise ConfigEntryAuthFailed("Missing OAuth access token")

        async def _refresh_token() -> str:
            await oauth_session.async_ensure_token_valid()
            try:
                token = oauth_session.token.get(CONF_ACCESS_TOKEN)
            except KeyError as err:
                raise ConfigEntryAuthFailed("Missing OAuth token payload") from err
            if not isinstance(token, str) or not token:
                raise ConfigEntryAuthFailed("Missing OAuth access token")
            return token

        api = _create_api_client(
            session=session,
            token=access_token,
            refresh_token_function=_refresh_token,
        )
        return api, oauth_session

    token = entry.data.get(CONF_ENTRY_API_KEY)
    if not isinstance(token, str) or not token:
        raise ConfigEntryAuthFailed("Missing SmartThings API token")

    return _create_api_client(session=session, token=token), None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Samsung Soundbar from a config entry."""
    api, oauth_session = await _build_api_for_entry(hass, entry)

    device_id = entry.data.get(CONF_ENTRY_DEVICE_ID)
    if not isinstance(device_id, str) or not device_id:
        raise ConfigEntryError("Missing SmartThings device id")

    try:
        smart_things_device = await _fetch_device(api, device_id)
    except Exception as err:  # noqa: BLE001
        if _is_auth_error(err):
            raise ConfigEntryAuthFailed from err
        if _is_not_found_error(err):
            raise ConfigEntryError(f"SmartThings device '{device_id}' not found") from err
        if _is_connection_error(err) or isinstance(err, ClientError):
            raise ConfigEntryNotReady from err
        if _is_smartthings_error(err):
            raise ConfigEntryNotReady from err
        raise

    max_volume = entry.data.get(CONF_ENTRY_MAX_VOLUME, 100)
    if not isinstance(max_volume, int):
        max_volume = 100

    soundbar_device = SoundbarDevice(
        smart_things_device,
        api,
        None,
        max_volume,
        entry.data.get(CONF_ENTRY_DEVICE_NAME),
        enable_eq=bool(entry.data.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR)),
        enable_advanced_audio=bool(
            entry.data.get(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES)
        ),
        enable_soundmode=bool(entry.data.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR)),
        enable_woofer=bool(entry.data.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER)),
    )
    await soundbar_device.update()

    entry.runtime_data = SoundbarRuntimeData(
        api=api,
        device=soundbar_device,
        oauth_session=oauth_session,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime_data = getattr(entry, "runtime_data", None)
    if isinstance(runtime_data, SoundbarRuntimeData):
        await runtime_data.api.close()
    return True
