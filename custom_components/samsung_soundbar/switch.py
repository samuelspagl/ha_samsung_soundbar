import logging

from homeassistant.components.switch import SwitchEntity
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
                SoundbarSwitchAdvancedAudio(
                    device,
                    "nightmode",
                    lambda: device.night_mode,
                    device.set_night_mode,
                    device.set_night_mode,
                )
            )
            entities.append(
                SoundbarSwitchAdvancedAudio(
                    device,
                    "bassmode",
                    lambda: device.bass_mode,
                    device.set_bass_mode,
                    device.set_bass_mode,
                )
            )
            entities.append(
                SoundbarSwitchAdvancedAudio(
                    device,
                    "voice_amplifier",
                    lambda: device.voice_amplifier,
                    device.set_voice_amplifier,
                    device.set_voice_amplifier,
                )
            )
    async_add_entities(entities)
    return True


class SoundbarSwitchAdvancedAudio(SwitchEntity):
    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        state_function,
        on_function,
        off_function,
    ):
        self.entity_id = f"switch.{device.device_name}_{append_unique_id}"

        self.__device = device
        self._name = f"{self.__device.device_name} {append_unique_id}"
        self._attr_unique_id = f"{device.device_id}_sw_{append_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.__device.device_id)},
            name=self.__device.device_name,
            manufacturer=self.__device.manufacturer,
            model=self.__device.model,
            sw_version=self.__device.firmware_version,
        )

        self.__state_function = state_function
        self.__state = False
        self.__on_function = on_function
        self.__off_function = off_function

    # ---------- GENERAL ---------------

    @property
    def name(self):
        return self._name

    def update(self):
        self.__state = self.__state_function()

    # ------ STATE FUNCTIONS --------
    @property
    def state(self):
        return "on" if self.__state else "off"

    async def async_turn_off(self):
        await self.__off_function(False)
        self.__state = "off"

    async def async_turn_on(self):
        await self.__on_function(True)
        self.__state = "on"
