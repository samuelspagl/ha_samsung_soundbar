from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_DEVICE_ID, CONF_ENTRY_SETTINGS_WOOFER_NUMBER, DOMAIN
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities: list[NumberEntity] = []

    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        coordinator = device_config.coordinator

        if device.device_id != config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            continue

        if config_entry.data.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER):
            entities.append(WooferLevelNumber(coordinator))

    async_add_entities(entities)
    return True


class WooferLevelNumber(CoordinatorEntity, NumberEntity):
    entity_description = NumberEntityDescription(
        key="woofer_level",
        native_min_value=-12,
        native_max_value=6,
        native_step=1,
        native_unit_of_measurement="dB",
        mode=NumberMode.BOX,
    )

    def __init__(self, coordinator):
        super().__init__(coordinator)
        dev: SoundbarDevice = coordinator.data

        self._attr_unique_id = f"{dev.device_id}_woofer_level"
        self._attr_name = "Woofer Level"
        self._attr_icon = "mdi:subwoofer"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev.device_id)},
            name=dev.device_name,
            manufacturer=dev.manufacturer,
            model=dev.model,
            sw_version=dev.firmware_version,
        )

    @property
    def native_value(self) -> float | None:
        dev: SoundbarDevice = self.coordinator.data
        try:
            return float(dev.woofer_level)
        except Exception:
            return None

    async def async_set_native_value(self, value: float):
        dev: SoundbarDevice = self.coordinator.data
        await dev.set_woofer(int(value))
        await self.coordinator.async_request_refresh()

