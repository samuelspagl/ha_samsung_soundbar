from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_DEVICE_ID, DOMAIN
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities: list[ButtonEntity] = []

    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        coordinator = device_config.coordinator
        if device.device_id != config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            continue

        entities.extend(
            [
                SoundbarButton(
                    coordinator,
                    key="refresh",
                    name="Refresh",
                    icon="mdi:refresh",
                    press=lambda d: coordinator.async_request_refresh(),
                ),
                SoundbarButton(
                    coordinator,
                    key="next_input_source",
                    name="Next Input Source",
                    icon="mdi:skip-next",
                    press=lambda d: d.device.command(
                        "main", "samsungvd.audioInputSource", "setNextInputSource"
                    ),
                ),
            ]
        )

    async_add_entities(entities)
    return True


class SoundbarButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, *, key: str, name: str, icon: str, press):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._press = press

        dev: SoundbarDevice = coordinator.data
        self._attr_unique_id = f"{dev.device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev.device_id)},
            name=dev.device_name,
            manufacturer=dev.manufacturer,
            model=dev.model,
            sw_version=dev.firmware_version,
        )

    async def async_press(self) -> None:
        dev: SoundbarDevice = self.coordinator.data
        await self._press(dev)
        await self.coordinator.async_request_refresh()

