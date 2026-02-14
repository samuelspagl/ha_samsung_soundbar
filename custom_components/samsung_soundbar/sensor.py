"""Sensor platform for Samsung Soundbar."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import DOMAIN
from .models import SoundbarRuntimeData


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities) -> bool:
    """Set up sensor entities from a config entry."""
    runtime_data: SoundbarRuntimeData = config_entry.runtime_data
    async_add_entities(
        [VolumeSensor(runtime_data.device, "volume_level", "mdi:volume-high")]
    )
    return True


class VolumeSensor(SensorEntity):
    """Volume sensor for soundbar."""

    def __init__(self, device: SoundbarDevice, append_unique_id: str, icon_string: str):
        """Initialize sensor."""
        self.entity_id = f"sensor.{device.device_name}_{append_unique_id}"
        self.__device = device
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
        self.__base_icon = icon_string
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.__device.device_id)},
            name=self.__device.device_name,
            manufacturer=self.__device.manufacturer,
            model=self.__device.model,
            sw_version=self.__device.firmware_version,
        )
        self.__append_unique_id = append_unique_id

    @property
    def name(self):
        return self.__append_unique_id

    @property
    def icon(self) -> str | None:
        return self.__base_icon

    @property
    def native_value(self) -> float | None:
        return self.__device.volume_level
