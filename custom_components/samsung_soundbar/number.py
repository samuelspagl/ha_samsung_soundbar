import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import DeviceInfo

from .models import DeviceConfig
from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_DEVICE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]

    entities = []
    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        if device.device_id == config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            entities.append(
                SoundbarNumberEntity(
                    device,
                    "woofer_level",
                    device.woofer_level,
                    device.set_woofer,
                    (-6, 12),
                )
            )
    async_add_entities(entities)
    return True


class SoundbarNumberEntity(NumberEntity):
    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        state_function,
        on_function,
        min_max: tuple,
    ):
        self.entity_id = f"number.{device.device_name}_{append_unique_id}"

        self.__device = device
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.__device.device_id)},
            name=self.__device.device_name,
            manufacturer=self.__device.manufacturer,
            model=self.__device.model,
            sw_version=self.__device.firmware_version,
        )

        self.__current_value_function = state_function
        self.__set_value_function = on_function
        self.__min_value = min_max[0]
        self.__max_value = min_max[1]

    # ---------- GENERAL ---------------

    @property
    def name(self):
        return self.__device.device_name

    # ------ STATE FUNCTIONS --------

    @property
    def native_value(self) -> float | None:
        return self.__current_value_function

    async def async_set_native_value(self, value: float):
        if value > self.__max_value:
            value = self.__min_value
        if value < self.__min_value:
            value = self.__min_value
        await self.__set_value_function(value)
