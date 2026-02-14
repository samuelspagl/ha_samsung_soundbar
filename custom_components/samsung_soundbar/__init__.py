"""The Samsung Soundbar integration."""

from __future__ import annotations

import logging

from aiohttp import ClientError
from pysmartthings import (
    SmartThings,
    SmartThingsAuthenticationFailedError,
    SmartThingsConnectionError,
    SmartThingsError,
    SmartThingsForbiddenError,
    SmartThingsNotFoundError,
)

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

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SWITCH,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


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

        api = SmartThings(session=session, _token=access_token)

        async def _refresh_token() -> str:
            await oauth_session.async_ensure_token_valid()
            try:
                token = oauth_session.token.get(CONF_ACCESS_TOKEN)
            except KeyError as err:
                raise ConfigEntryAuthFailed("Missing OAuth token payload") from err
            if not isinstance(token, str) or not token:
                raise ConfigEntryAuthFailed("Missing OAuth access token")
            return token

        api.refresh_token_function = _refresh_token
        return api, oauth_session

    token = entry.data.get(CONF_ENTRY_API_KEY)
    if not isinstance(token, str) or not token:
        raise ConfigEntryAuthFailed("Missing SmartThings API token")

    return SmartThings(session=session, _token=token), None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Samsung Soundbar from a config entry."""
    api, oauth_session = await _build_api_for_entry(hass, entry)

    device_id = entry.data.get(CONF_ENTRY_DEVICE_ID)
    if not isinstance(device_id, str) or not device_id:
        raise ConfigEntryError("Missing SmartThings device id")

    try:
        smart_things_device = await api.get_device(device_id)
    except (SmartThingsAuthenticationFailedError, SmartThingsForbiddenError) as err:
        raise ConfigEntryAuthFailed from err
    except SmartThingsNotFoundError as err:
        raise ConfigEntryError(f"SmartThings device '{device_id}' not found") from err
    except (SmartThingsConnectionError, ClientError) as err:
        raise ConfigEntryNotReady from err
    except SmartThingsError as err:
        raise ConfigEntryNotReady from err

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
