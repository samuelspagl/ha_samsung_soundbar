import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pysmartthings import SmartThings

from .api_extension.SoundbarDevice import SoundbarDevice
from .config_flow import DEFAULT_OPTIONS
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


async def _async_get_access_token(hass: HomeAssistant, entry: ConfigEntry) -> str:
    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    await oauth_session.async_ensure_token_valid()
    return oauth_session.token[CONF_ACCESS_TOKEN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up component from a config entry, config_entry contains data from config entry database."""
    _LOGGER.info("[%s] Starting to setup a ConfigEntry", DOMAIN)
    _LOGGER.debug("[%s] Setting up ConfigEntry with the following data: %s", DOMAIN, entry.data)

    token = await _async_get_access_token(hass, entry)

    if DOMAIN not in hass.data:
        _LOGGER.debug("[%s] Domain not found in hass.data setting default", DOMAIN)
        hass.data[DOMAIN] = SoundbarConfig(
            SmartThings(async_get_clientsession(hass), token),
            {},
        )

    domain_config: SoundbarConfig = hass.data[DOMAIN]
    domain_config.api.token = token
    _LOGGER.debug("[%s] Retrieved Domain Config: %s", DOMAIN, domain_config)

    options = {**DEFAULT_OPTIONS, **entry.options}

    if entry.data.get(CONF_ENTRY_DEVICE_ID) not in domain_config.devices:
        _LOGGER.info("[%s] Setting up new Soundbar device", DOMAIN)
        _LOGGER.debug(
            "[%s] DeviceId: %s not found in domain_config, setting up new device.",
            DOMAIN,
            entry.data.get(CONF_ENTRY_DEVICE_ID),
        )
        smart_things_device = await domain_config.api.device(entry.data.get(CONF_ENTRY_DEVICE_ID))
        session = async_get_clientsession(hass)

        soundbar_device = SoundbarDevice(
            device=smart_things_device,
            smartthings=domain_config.api,
            session=session,
            max_volume=options.get(CONF_ENTRY_MAX_VOLUME),
            device_name=entry.data.get(CONF_ENTRY_DEVICE_NAME),
            enable_eq=options.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR),
            enable_advanced_audio=options.get(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES),
            enable_soundmode=options.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR),
            enable_woofer=options.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER),
        )
        await soundbar_device.update()
        domain_config.devices[entry.data.get(CONF_ENTRY_DEVICE_ID)] = DeviceConfig(
            {**entry.data, **options}, soundbar_device
        )
        _LOGGER.info("[%s] Successfully initialized new Soundbar device", DOMAIN)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
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


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options/token change."""
    await hass.config_entries.async_reload(entry.entry_id)
