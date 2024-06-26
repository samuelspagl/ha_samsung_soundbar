import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pysmartthings import SmartThings

from .api_extension.SoundbarDevice import SoundbarDevice
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
    SUPPORTED_DOMAINS,
)
from .models import DeviceConfig, SoundbarConfig

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["media_player", "switch", "image", "number", "select", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up component from a config entry, config_entry contains data from config entry database."""
    # store shell object

    _LOGGER.info(f"[{DOMAIN}] Starting to setup a ConfigEntry")
    _LOGGER.debug(
        f"[{DOMAIN}] Setting up ConfigEntry with the following data: {entry.data}"
    )
    if not DOMAIN in hass.data:
        _LOGGER.debug(f"[{DOMAIN}] Domain not found in hass.data setting default")
        hass.data[DOMAIN] = SoundbarConfig(
            SmartThings(
                async_get_clientsession(hass), entry.data.get(CONF_ENTRY_API_KEY)
            ),
            {},
        )

    domain_config: SoundbarConfig = hass.data[DOMAIN]
    _LOGGER.debug(f"[{DOMAIN}] Retrieved Domain Config: {domain_config}")

    if not entry.data.get(CONF_ENTRY_DEVICE_ID) in domain_config.devices:
        _LOGGER.info(f"[{DOMAIN}] Setting up new Soundbar device")
        _LOGGER.debug(
            f"[{DOMAIN}] DeviceId: {entry.data.get(CONF_ENTRY_DEVICE_ID)} not found in domain_config, setting up new device."
        )
        smart_things_device = await domain_config.api.device(
            entry.data.get(CONF_ENTRY_DEVICE_ID)
        )
        session = async_get_clientsession(hass)
        soundbar_device = SoundbarDevice(
            smart_things_device,
            session,
            entry.data.get(CONF_ENTRY_MAX_VOLUME),
            entry.data.get(CONF_ENTRY_DEVICE_NAME),
            enable_eq=entry.data.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR),
            enable_advanced_audio=entry.data.get(
                CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES
            ),
            enable_soundmode=entry.data.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR),
            enable_woofer=entry.data.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER),
        )
        await soundbar_device.update()
        domain_config.devices[entry.data.get(CONF_ENTRY_DEVICE_ID)] = DeviceConfig(
            entry.data, soundbar_device
        )
        _LOGGER.info(f"[{DOMAIN}] Successfully initialized new Soundbar device")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    domain_data = hass.data[DOMAIN]
    if unload_ok:
        del domain_data.devices[entry.data.get(CONF_ENTRY_DEVICE_ID)]
        if len(domain_data.devices) == 0:
            del hass.data[DOMAIN]

    return unload_ok
