"""Image platform for Samsung Soundbar."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import UndefinedType

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import DOMAIN
from .models import SoundbarRuntimeData


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities) -> bool:
    """Set up image entities from a config entry."""
    runtime_data: SoundbarRuntimeData = config_entry.runtime_data
    async_add_entities([SoundbarImageEntity(runtime_data.device, "Image URL", hass)])
    return True


class SoundbarImageEntity(ImageEntity):
    """Image entity for album art."""

    def __init__(
        self, device: SoundbarDevice, append_unique_id: str, hass: HomeAssistant
    ) -> None:
        super().__init__(hass)
        self.entity_id = f"image.{device.device_name}_{append_unique_id}"
        self.__device = device
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.__device.device_id)},
            name=self.__device.device_name,
            manufacturer=self.__device.manufacturer,
            model=self.__device.model,
            sw_version=self.__device.firmware_version,
        )
        self.__updated = None

    @property
    def image_url(self) -> str | None | UndefinedType:
        """Return URL of image."""
        return self.__device.media_coverart_url

    @property
    def image_last_updated(self) -> datetime | None:
        """Return the timestamp of latest image update."""
        current = self.__device.media_coverart_updated
        if self.__updated != current:
            self._cached_image = None
            self.__updated = current
        return current

    @property
    def name(self):
        return self.__device.device_name
