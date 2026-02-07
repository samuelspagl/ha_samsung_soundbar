from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import (
    CONF_ENTRY_DEVICE_ID,
    CONF_ENTRY_SETTINGS_EQ_SELECTOR,
    CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
    DOMAIN,
)
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities: list[SelectEntity] = []

    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        coordinator = device_config.coordinator
        if device.device_id != config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            continue

        entities.append(InputSourceSelectEntity(coordinator))

        if config_entry.data.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR):
            entities.append(EqPresetSelectEntity(coordinator))

        if config_entry.data.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR):
            entities.append(SoundModeSelectEntity(coordinator))

    async_add_entities(entities)
    return True


class _BaseSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, desc: SelectEntityDescription, key: str, name: str, icon: str):
        super().__init__(coordinator)
        dev: SoundbarDevice = coordinator.data

        self.entity_description = desc
        self._attr_unique_id = f"{dev.device_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev.device_id)},
            name=dev.device_name,
            manufacturer=dev.manufacturer,
            model=dev.model,
            sw_version=dev.firmware_version,
        )


class InputSourceSelectEntity(_BaseSelect):
    def __init__(self, coordinator):
        super().__init__(
            coordinator,
            SelectEntityDescription(key="input_source"),
            key="select_input_source",
            name="Input Source",
            icon="mdi:video-input-hdmi",
        )

    @property
    def current_option(self) -> str | None:
        dev: SoundbarDevice = self.coordinator.data
        return dev.input_source

    @property
    def options(self) -> list[str]:
        dev: SoundbarDevice = self.coordinator.data
        return list(dev.supported_input_sources or [])

    async def async_select_option(self, option: str) -> None:
        dev: SoundbarDevice = self.coordinator.data
        await dev.select_source(option)
        await self.coordinator.async_request_refresh()


class EqPresetSelectEntity(_BaseSelect):
    def __init__(self, coordinator):
        super().__init__(
            coordinator,
            SelectEntityDescription(key="eq_preset"),
            key="select_eq_preset",
            name="EQ Preset",
            icon="mdi:tune-vertical",
        )

    @property
    def current_option(self) -> str | None:
        dev: SoundbarDevice = self.coordinator.data
        return dev.active_equalizer_preset

    @property
    def options(self) -> list[str]:
        dev: SoundbarDevice = self.coordinator.data
        return list(dev.supported_equalizer_presets or [])

    async def async_select_option(self, option: str) -> None:
        dev: SoundbarDevice = self.coordinator.data
        await dev.set_equalizer_preset(option)
        await self.coordinator.async_request_refresh()


class SoundModeSelectEntity(_BaseSelect):
    def __init__(self, coordinator):
        super().__init__(
            coordinator,
            SelectEntityDescription(key="sound_mode"),
            key="select_sound_mode",
            name="Sound Mode",
            icon="mdi:surround-sound",
        )

    @property
    def current_option(self) -> str | None:
        dev: SoundbarDevice = self.coordinator.data
        return dev.sound_mode

    @property
    def options(self) -> list[str]:
        dev: SoundbarDevice = self.coordinator.data
        return list(dev.supported_soundmodes or [])

    async def async_select_option(self, option: str) -> None:
        dev: SoundbarDevice = self.coordinator.data
        await dev.select_sound_mode(option)
        await self.coordinator.async_request_refresh()

