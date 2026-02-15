"""Number platform for Samsung Soundbar."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_SETTINGS_WOOFER_NUMBER, DOMAIN
from .models import SoundbarRuntimeData


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities) -> bool:
    """Set up number entities from a config entry."""
    if not config_entry.data.get(CONF_ENTRY_SETTINGS_WOOFER_NUMBER):
        return True

    runtime_data: SoundbarRuntimeData = config_entry.runtime_data
    async_add_entities(
        [
            SoundbarWooferNumberEntity(
                runtime_data.device,
                "woofer_level",
            )
        ]
    )
    return True


class SoundbarWooferNumberEntity(NumberEntity):
    """Woofer level entity."""

    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
    ) -> None:
        """Initialize number entity."""
        self.entity_id = f"number.{device.device_name}_{append_unique_id}"
        self.entity_description = NumberEntityDescription(
            native_max_value=6,
            native_min_value=-10,
            mode=NumberMode.BOX,
            native_step=1,
            native_unit_of_measurement="dB",
            key=append_unique_id,
        )
        self.__device = device
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
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
    def native_value(self) -> float | None:
        return self.__device.woofer_level

    async def async_set_native_value(self, value: float):
        await self.__device.set_woofer(int(value))
