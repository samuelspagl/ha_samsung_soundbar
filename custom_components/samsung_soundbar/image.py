import logging

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .models import DeviceConfig
from .api_extension.SoundbarDevice import SoundbarDevice
from .const import DOMAIN, CONF_ENTRY_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]

    entities = []
    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        if device.device_id == config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            entities.append(SoundbarImageEntity(device, "Image URL", hass))
    async_add_entities(entities)
    return True


class SoundbarImageEntity(ImageEntity):
    def __init__(
        self, device: SoundbarDevice, append_unique_id: str, hass: HomeAssistant
    ):
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

        self._attr_image_url = self.__device.media_coverart_url

    # ---------- GENERAL ---------------

    @property
    def name(self):
        return self.__device.device_name
