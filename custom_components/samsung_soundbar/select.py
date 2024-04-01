import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.entity import DeviceInfo

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import (
    CONF_ENTRY_DEVICE_ID,
    CONF_ENTRY_SETTINGS_EQ_SELECTOR,
    CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR,
    DOMAIN,
)
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities = []
    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        if device.device_id == config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            if config_entry.data.get(CONF_ENTRY_SETTINGS_EQ_SELECTOR):
                entities.append(
                    EqPresetSelectEntity(device, "eq_preset", "mdi:tune-vertical")
                )
            if config_entry.data.get(CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR):
                entities.append(
                    SoundModeSelectEntity(
                        device, "sound_mode_preset", "mdi:surround-sound"
                    )
                )

            entities.append(
                InputSelectEntity(device, "input_preset", "mdi:video-input-hdmi")
            )
    async_add_entities(entities)
    return True


class EqPresetSelectEntity(SelectEntity):
    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ):
        self.entity_id = f"number.{device.device_name}_{append_unique_id}"
        self.entity_description = SelectEntityDescription(
            key=append_unique_id,
        )
        self.__base_icon = icon_string
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

        self._attr_options = self.__device.supported_equalizer_presets

    # ---------- GENERAL ---------------

    @property
    def name(self):
        return self.__append_unique_id

    @property
    def icon(self) -> str | None:
        return self.__base_icon

    # ------ STATE FUNCTIONS --------

    @property
    def current_option(self) -> str | None:
        """Get the current status of the select entity from device_status."""
        return self.__device.active_equalizer_preset

    async def async_select_option(self, option: str) -> None:
        """Set the option."""

        await self.__device.set_equalizer_preset(option)


class SoundModeSelectEntity(SelectEntity):
    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ):
        self.entity_id = f"number.{device.device_name}_{append_unique_id}"
        self.entity_description = SelectEntityDescription(
            key=append_unique_id,
        )
        self.__base_icon = icon_string
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

        self._attr_options = self.__device.supported_soundmodes

    # ---------- GENERAL ---------------

    @property
    def name(self):
        return self.__append_unique_id

    @property
    def icon(self) -> str | None:
        return self.__base_icon

    # ------ STATE FUNCTIONS --------

    @property
    def current_option(self) -> str | None:
        """Get the current status of the select entity from device_status."""
        return self.__device.sound_mode

    async def async_select_option(self, option: str) -> None:
        """Set the option."""

        await self.__device.select_sound_mode(option)


class InputSelectEntity(SelectEntity):
    def __init__(
        self,
        device: SoundbarDevice,
        append_unique_id: str,
        icon_string: str,
    ):
        self.entity_id = f"number.{device.device_name}_{append_unique_id}"
        self.entity_description = SelectEntityDescription(
            key=append_unique_id,
        )
        self.__base_icon = icon_string
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

        self._attr_options = self.__device.supported_input_sources

    # ---------- GENERAL ---------------

    @property
    def name(self):
        return self.__append_unique_id

    @property
    def icon(self) -> str | None:
        return self.__base_icon

    # ------ STATE FUNCTIONS --------

    @property
    def current_option(self) -> str | None:
        """Get the current status of the select entity from device_status."""
        return self.__device.input_source

    async def async_select_option(self, option: str) -> None:
        """Set the option."""

        await self.__device.select_source(option)
