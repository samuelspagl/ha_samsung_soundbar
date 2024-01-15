import logging
from typing import Any, Mapping

from homeassistant.components.media_player import (DEVICE_CLASS_SPEAKER,
                                                   MediaPlayerEntity)
from homeassistant.components.media_player.const import (
    SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_SELECT_SOURCE, SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import (CONF_ENTRY_API_KEY, CONF_ENTRY_DEVICE_ID,
                    CONF_ENTRY_DEVICE_NAME, CONF_ENTRY_MAX_VOLUME, DOMAIN)
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartThings Soundbar"
CONF_MAX_VOLUME = "max_volume"

SUPPORT_SMARTTHINGS_SOUNDBAR = (
    SUPPORT_PAUSE
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_SET
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_TURN_OFF
    | SUPPORT_TURN_ON
    | SUPPORT_PLAY
    | SUPPORT_STOP
    | SUPPORT_SELECT_SOUND_MODE
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]

    entities = []
    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        session = async_get_clientsession(hass)
        device = device_config.device
        if device.device_id == config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            entity_id = generate_entity_id(
                "media_player.{}", device.device_name, hass=hass
            )
            entities.append(SmartThingsSoundbarMediaPlayer(device, entity_id, session))
    async_add_entities(entities)
    return True


class SmartThingsSoundbarMediaPlayer(MediaPlayerEntity):
    def __init__(self, device: SoundbarDevice, entity_id: str, session):
        self.session = session
        self.device = device
        self.entity_id = entity_id
        self._attr_unique_id = f"{self.device.device_id}_mp"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device.device_id)},
            name=self.device.device_name,
            manufacturer=self.device.manufacturer,
            model=self.device.model,
            sw_version=self.device.firmware_version,
        )

    async def async_update(self):
        await self.device.update()

    # ---------- GENERAL SETTINGS ------------

    @property
    def device_class(self):
        return DEVICE_CLASS_SPEAKER

    @property
    def supported_features(self):
        return SUPPORT_SMARTTHINGS_SOUNDBAR

    @property
    def name(self):
        return self.device.device_name

    # ---------- POWER ON/OFF ------------

    @property
    def state(self):
        return self.device.state

    async def async_turn_off(self):
        await self.device.switch_off()

    async def async_turn_on(self):
        await self.device.switch_on()

    # ---------- VOLUME ------------
    @property
    def volume_level(self):
        return self.device.volume_level

    @property
    def is_volume_muted(self):
        return self.device.volume_muted

    async def async_set_volume_level(self, volume):
        await self.device.set_volume(volume)

    async def async_mute_volume(self, mute):
        await self.device.mute_volume(mute)

    async def async_volume_up(self):
        await self.device.volume_up()

    async def async_volume_down(self):
        await self.device.volume_down()

    # ---------- INPUT SOURCES ------------

    @property
    def source(self):
        return self.device.input_source

    @property
    def source_list(self):
        return self.device.supported_input_sources

    async def async_select_source(self, source):
        await self.device.select_source(source)

    # ---------- SOUND MODE ------------

    @property
    def sound_mode(self) -> str | None:
        return self.device.sound_mode

    @property
    def sound_mode_list(self) -> list[str] | None:
        return self.device.supported_soundmodes

    async def async_select_sound_mode(self, sound_mode):
        await self.device.select_sound_mode(sound_mode)

    # ---------- MEDIA ------------
    @property
    def media_title(self):
        return self.device.media_title

    @property
    def media_artist(self) -> str | None:
        return self.device.media_artist

    @property
    def media_duration(self) -> int | None:
        return self.device.media_duration

    @property
    def media_position(self):
        return self.device.media_position

    @property
    def media_image_url(self) -> str | None:
        return self.device.media_coverart_url

    @property
    def app_name(self) -> str | None:
        return self.device.media_app_name

    async def async_media_play(self):
        await self.device.media_play()

    async def async_media_pause(self):
        await self.device.media_pause()

    async def async_media_stop(self):
        await self.device.media_stop()

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {"device_information": self.device.retrieve_data}
