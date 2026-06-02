import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pysmartthings import SmartThings
from pysmartthings.exceptions import SmartThingsAuthenticationFailedError

from .api_extension.SoundbarDevice import SoundbarDevice
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
from .models import DeviceConfig, SoundbarConfig

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["media_player", "switch", "image", "number", "select", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Samsung Soundbar from config entry."""

    _LOGGER.info("[%s] Setting up entry", DOMAIN)

    token = entry.data[CONF_ACCESS_TOKEN]

    api = SmartThings(session=async_get_clientsession(hass))
    api.authenticate(token)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = SoundbarConfig(api, {})

    domain_config: SoundbarConfig = hass.data[DOMAIN]
    domain_config.api = api

    device_id = entry.data.get(CONF_ENTRY_DEVICE_ID)

    if device_id not in domain_config.devices:

        try:
            _LOGGER.debug(
                "[%s] Validating SmartThings authentication for device %s",
                DOMAIN,
                device_id,
            )

            smart_things_device = await api.get_device(device_id)

        except SmartThingsAuthenticationFailedError as err:
            _LOGGER.error(
                "[%s] SmartThings authentication failed. "
                "The token may have expired, been revoked, or is no longer valid.",
                DOMAIN,
            )

            raise ConfigEntryAuthFailed(
                "SmartThings token is no longer valid"
            ) from err

        except Exception as err:
            _LOGGER.exception(
                "[%s] Unexpected error while loading device %s",
                DOMAIN,
                device_id,
            )
            raise

        session = async_get_clientsession(hass)

        soundbar_device = SoundbarDevice(
            device=smart_things_device,
            smartthings=api,
            session=session,
            max_volume=entry.options.get(CONF_ENTRY_MAX_VOLUME, 100),
            device_name=entry.data.get(CONF_ENTRY_DEVICE_NAME),
            enable_eq=entry.options.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR, False),
            enable_advanced_audio=entry.options.get(
                CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, False
            ),
            enable_soundmode=entry.options.get(
                CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR, False
            ),
            enable_woofer=entry.options.get(
                CONF_ENTRY_SETTINGS_WOOFER_NUMBER, False
            ),
        )

        await soundbar_device.update()

        domain_config.devices[device_id] = DeviceConfig(
            entry.data,
            soundbar_device,
        )

        _LOGGER.info("[%s] Device initialized successfully", DOMAIN)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        domain_data = hass.data.get(DOMAIN)
        if domain_data:
            domain_data.devices.pop(entry.data.get(CONF_ENTRY_DEVICE_ID), None)
            if not domain_data.devices:
                hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
