import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass

from .models import DeviceConfig
from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_DEVICE_ID, DOMAIN
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities = []
    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device

        if device.device_id == config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            entities.append(
                VolumeSensor(device, "volume_level")
            )
    async_add_entities(entities)
    return True



class VolumeSensor(SensorEntity):
    def __init__(self, device: SoundbarDevice, append_unique_id: str):
        self.entity_id = f"sensor.{device.device_name}_{append_unique_id}"
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

        _attr_device_class = SensorDeviceClass.VOLUME

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._attr_native_value = self.__device.device.status.volume
