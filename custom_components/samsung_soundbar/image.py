from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import UndefinedType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_DEVICE_ID, DOMAIN
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities: list[ImageEntity] = []

    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        coordinator = device_config.coordinator
        if device.device_id != config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            continue
        entities.append(SoundbarCoverArtImage(coordinator, hass))

    async_add_entities(entities)
    return True


class SoundbarCoverArtImage(CoordinatorEntity, ImageEntity):
    def __init__(self, coordinator, hass: HomeAssistant) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)

        dev: SoundbarDevice = coordinator.data
        self._attr_unique_id = f"{dev.device_id}_cover_art"
        self._attr_name = "Cover Art"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev.device_id)},
            name=dev.device_name,
            manufacturer=dev.manufacturer,
            model=dev.model,
            sw_version=dev.firmware_version,
        )
        self.__updated: datetime | None = None

    @property
    def image_url(self) -> str | None | UndefinedType:
        dev: SoundbarDevice = self.coordinator.data
        return dev.media_coverart_url

    @property
    def image_last_updated(self) -> datetime | None:
        dev: SoundbarDevice = self.coordinator.data
        current = dev.media_coverart_updated
        if self.__updated != current:
            self._cached_image = None
            self.__updated = current
        return current

