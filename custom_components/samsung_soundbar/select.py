"""Select platform for Samsung Soundbar."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import (
    CONF_ENTRY_SETTINGS_EQ_SELECTOR,
    CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
    DOMAIN,
)
from .models import SoundbarRuntimeData


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities) -> bool:
    """Set up select entities from a config entry."""
    runtime_data: SoundbarRuntimeData = config_entry.runtime_data
    device = runtime_data.device
    entities: list[SelectEntity] = []

    if config_entry.data.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR):
        entities.append(EqPresetSelectEntity(device, "eq_preset", "mdi:tune-vertical"))

    if config_entry.data.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR):
        entities.append(
            SoundModeSelectEntity(
                device,
                "sound_mode_preset",
                "mdi:surround-sound",
            )
        )

    entities.append(InputSelectEntity(device, "input_preset", "mdi:video-input-hdmi"))
    async_add_entities(entities)
    return True


class _BaseSoundbarSelectEntity(SelectEntity):
    """Base class for soundbar select entities."""

    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ) -> None:
        """Initialize select entity."""
        self.entity_id = f"number.{device.device_name}_{append_unique_id}"
        self.entity_description = SelectEntityDescription(key=append_unique_id)
        self.__base_icon = icon_string
        self._device = device
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            name=self._device.device_name,
            manufacturer=self._device.manufacturer,
            model=self._device.model,
            sw_version=self._device.firmware_version,
        )
        self.__append_unique_id = append_unique_id

    @property
    def name(self):
        return self.__append_unique_id

    @property
    def icon(self) -> str | None:
        return self.__base_icon


class EqPresetSelectEntity(_BaseSoundbarSelectEntity):
    """Entity to select equalizer preset."""

    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ) -> None:
        super().__init__(device, append_unique_id, icon_string)
        self._attr_options = self._device.supported_equalizer_presets

    @property
    def current_option(self) -> str | None:
        return self._device.active_equalizer_preset

    async def async_select_option(self, option: str) -> None:
        await self._device.set_equalizer_preset(option)


class SoundModeSelectEntity(_BaseSoundbarSelectEntity):
    """Entity to select sound mode."""

    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ) -> None:
        super().__init__(device, append_unique_id, icon_string)
        self._attr_options = self._device.supported_soundmodes

    @property
    def current_option(self) -> str | None:
        return self._device.sound_mode

    async def async_select_option(self, option: str) -> None:
        await self._device.select_sound_mode(option)


class InputSelectEntity(_BaseSoundbarSelectEntity):
    """Entity to select input source."""

    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ) -> None:
        super().__init__(device, append_unique_id, icon_string)
        self._attr_options = self._device.supported_input_sources

    @property
    def current_option(self) -> str | None:
        return self._device.input_source

    async def async_select_option(self, option: str) -> None:
        await self._device.select_source(option)
