"""Switch platform for Samsung Soundbar."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES, DOMAIN
from .models import SoundbarRuntimeData


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities) -> bool:
    """Set up switch entities from a config entry."""
    if not config_entry.data.get(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES):
        return True

    runtime_data: SoundbarRuntimeData = config_entry.runtime_data
    device = runtime_data.device
    async_add_entities(
        [
            SoundbarSwitchAdvancedAudio(
                device,
                "nightmode",
                lambda: device.night_mode,
                device.set_night_mode,
                device.set_night_mode,
                "mdi:weather-night",
            ),
            SoundbarSwitchAdvancedAudio(
                device,
                "bassmode",
                lambda: device.bass_mode,
                device.set_bass_mode,
                device.set_bass_mode,
                "mdi:speaker-wireless",
            ),
            SoundbarSwitchAdvancedAudio(
                device,
                "voice_amplifier",
                lambda: device.voice_amplifier,
                device.set_voice_amplifier,
                device.set_voice_amplifier,
                "mdi:account-voice",
            ),
        ]
    )
    return True


class SoundbarSwitchAdvancedAudio(SwitchEntity):
    """Advanced-audio toggle switch."""

    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        state_function: Callable[[], bool],
        on_function,
        off_function,
        icon_string: str = "mdi:toggle-switch-variant",
    ) -> None:
        """Initialize switch."""
        self.entity_id = f"switch.{device.device_name}_{append_unique_id}"
        self.__device = device
        self._name = f"{self.__device.device_name} {append_unique_id}"
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
        self.__base_icon = icon_string
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.__device.device_id)},
            name=self.__device.device_name,
            manufacturer=self.__device.manufacturer,
            model=self.__device.model,
            sw_version=self.__device.firmware_version,
        )
        self.__state_function = state_function
        self.__on_function = on_function
        self.__off_function = off_function

    @property
    def name(self):
        return self._name

    @property
    def icon(self) -> str | None:
        return self.__base_icon

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return bool(self.__state_function())

    async def async_turn_off(self):
        await self.__off_function(False)

    async def async_turn_on(self):
        await self.__on_function(True)
