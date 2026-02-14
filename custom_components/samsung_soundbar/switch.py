from __future__ import annotations

import logging
from typing import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import (
    CONF_ENTRY_DEVICE_ID,
    CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES,
    DOMAIN,
)
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities: list[SwitchEntity] = []

    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        coordinator = device_config.coordinator

        if device.device_id != config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            continue

        if config_entry.data.get(CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES):
            entities.extend(
                [
                    SoundbarBoolSwitch(
                        coordinator,
                        key="night_mode",
                        name="Night Mode",
                        icon="mdi:weather-night",
                        getter=lambda d: d.night_mode,
                        setter=lambda d, v: d.set_night_mode(v),
                    ),
                    SoundbarBoolSwitch(
                        coordinator,
                        key="bass_boost",
                        name="Bass Boost",
                        icon="mdi:speaker-wireless",
                        getter=lambda d: d.bass_mode,
                        setter=lambda d, v: d.set_bass_mode(v),
                    ),
                    SoundbarBoolSwitch(
                        coordinator,
                        key="voice_amplifier",
                        name="Voice Amplifier",
                        icon="mdi:account-voice",
                        getter=lambda d: d.voice_amplifier,
                        setter=lambda d, v: d.set_voice_amplifier(v),
                    ),
                ]
            )

    async_add_entities(entities)
    return True


class SoundbarBoolSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(
        self,
        coordinator,
        *,
        key: str,
        name: str,
        icon: str,
        getter: Callable[[SoundbarDevice], bool],
        setter: Callable[[SoundbarDevice, bool], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._getter = getter
        self._setter = setter

        dev: SoundbarDevice = coordinator.data
        self._attr_unique_id = f"{dev.device_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        # For newer models execute/status may be unavailable, so treat as assumed state.
        self._attr_assumed_state = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev.device_id)},
            name=dev.device_name,
            manufacturer=dev.manufacturer,
            model=dev.model,
            sw_version=dev.firmware_version,
        )

    @property
    def is_on(self) -> bool | None:
        dev: SoundbarDevice = self.coordinator.data
        try:
            return bool(self._getter(dev))
        except Exception:
            return None

    async def async_turn_on(self, **kwargs):
        dev: SoundbarDevice = self.coordinator.data
        await self._setter(dev, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        dev: SoundbarDevice = self.coordinator.data
        await self._setter(dev, False)
        await self.coordinator.async_request_refresh()

