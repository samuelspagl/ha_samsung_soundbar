"""Media player platform for Samsung Soundbar."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
import voluptuous as vol

from .api_extension.SoundbarDevice import SoundbarDevice
from .api_extension.const import RearSpeakerMode, SpeakerIdentifier
from .const import DOMAIN
from .models import SoundbarRuntimeData

SUPPORT_SMARTTHINGS_SOUNDBAR = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
)


def _register_services() -> None:
    """Register media-player services for this integration."""

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "select_soundmode",
        cv.make_entity_service_schema({vol.Required("sound_mode"): str}),
        SmartThingsSoundbarMediaPlayer.async_select_sound_mode.__name__,
    )
    platform.async_register_entity_service(
        "set_woofer_level",
        cv.make_entity_service_schema(
            {vol.Required("level"): vol.All(int, vol.Range(min=-12, max=6))}
        ),
        SmartThingsSoundbarMediaPlayer.async_set_woofer_level.__name__,
    )
    platform.async_register_entity_service(
        "set_night_mode",
        cv.make_entity_service_schema({vol.Required("enabled"): bool}),
        SmartThingsSoundbarMediaPlayer.async_set_night_mode.__name__,
    )
    platform.async_register_entity_service(
        "set_bass_enhancer",
        cv.make_entity_service_schema({vol.Required("enabled"): bool}),
        SmartThingsSoundbarMediaPlayer.async_set_bass_mode.__name__,
    )
    platform.async_register_entity_service(
        "set_voice_enhancer",
        cv.make_entity_service_schema({vol.Required("enabled"): bool}),
        SmartThingsSoundbarMediaPlayer.async_set_voice_mode.__name__,
    )
    platform.async_register_entity_service(
        "set_speaker_level",
        cv.make_entity_service_schema(
            {vol.Required("speaker_identifier"): str, vol.Required("level"): int}
        ),
        SmartThingsSoundbarMediaPlayer.async_set_speaker_level.__name__,
    )
    platform.async_register_entity_service(
        "set_rear_speaker_mode",
        cv.make_entity_service_schema({vol.Required("speaker_mode"): str}),
        SmartThingsSoundbarMediaPlayer.async_set_rear_speaker_mode.__name__,
    )
    platform.async_register_entity_service(
        "set_active_voice_amplifier",
        cv.make_entity_service_schema({vol.Required("enabled"): bool}),
        SmartThingsSoundbarMediaPlayer.async_set_active_voice_amplifier.__name__,
    )
    platform.async_register_entity_service(
        "set_space_fit_sound",
        cv.make_entity_service_schema({vol.Required("enabled"): bool}),
        SmartThingsSoundbarMediaPlayer.async_set_space_fit_sound.__name__,
    )


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities) -> bool:
    """Set up media_player from a config entry."""
    _register_services()

    runtime_data: SoundbarRuntimeData = config_entry.runtime_data
    entity_id = generate_entity_id(
        "media_player.{}",
        runtime_data.device.device_name,
        hass=hass,
    )
    async_add_entities([SmartThingsSoundbarMediaPlayer(runtime_data.device, entity_id)])
    return True


class SmartThingsSoundbarMediaPlayer(MediaPlayerEntity):
    """Representation of the Samsung Soundbar media player."""

    def __init__(self, device: SoundbarDevice, entity_id: str):
        """Initialize entity."""
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

    async def async_update(self) -> None:
        await self.device.update()

    @property
    def device_class(self):
        return MediaPlayerDeviceClass.SPEAKER

    @property
    def supported_features(self):
        return SUPPORT_SMARTTHINGS_SOUNDBAR

    @property
    def name(self):
        return self.device.device_name

    @property
    def state(self):
        return self.device.state

    async def async_turn_off(self):
        await self.device.switch_off()

    async def async_turn_on(self):
        await self.device.switch_on()

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

    @property
    def source(self):
        return self.device.input_source

    @property
    def source_list(self):
        return self.device.supported_input_sources

    async def async_select_source(self, source):
        await self.device.select_source(source)

    @property
    def sound_mode(self) -> str | None:
        return self.device.sound_mode

    @property
    def sound_mode_list(self) -> list[str] | None:
        return self.device.supported_soundmodes

    async def async_select_sound_mode(self, sound_mode):
        await self.device.select_sound_mode(sound_mode)

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

    async def async_media_next_track(self):
        await self.device.media_next_track()

    async def async_media_previous_track(self):
        await self.device.media_previous_track()

    async def async_media_stop(self):
        await self.device.media_stop()

    async def async_set_woofer_level(self, level: int):
        await self.device.set_woofer(level)

    async def async_set_bass_mode(self, enabled: bool):
        await self.device.set_bass_mode(enabled)

    async def async_set_voice_mode(self, enabled: bool):
        await self.device.set_voice_amplifier(enabled)

    async def async_set_night_mode(self, enabled: bool):
        await self.device.set_night_mode(enabled)

    async def async_set_speaker_level(self, speaker_identifier: str, level: int):
        await self.device.set_speaker_level(
            SpeakerIdentifier(speaker_identifier),
            level,
        )

    async def async_set_rear_speaker_mode(self, speaker_mode: str):
        await self.device.set_rear_speaker_mode(RearSpeakerMode(speaker_mode))

    async def async_set_active_voice_amplifier(self, enabled: bool):
        await self.device.set_active_voice_amplifier(enabled)

    async def async_set_space_fit_sound(self, enabled: bool):
        await self.device.set_space_fit_sound(enabled)
