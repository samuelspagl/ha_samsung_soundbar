from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import CONF_ENTRY_DEVICE_ID, DOMAIN
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _SensorSpec:
    key: str
    name: str
    icon: str | None
    value: Callable[[SoundbarDevice], Any]
    attrs: Callable[[SoundbarDevice], dict[str, Any]] | None = None
    enabled_by_default: bool = True


def _attrs_from(device: SoundbarDevice, keys: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in keys:
        v = device._attr(k)  # pylint: disable=protected-access
        if v is not None:
            out[k] = v
    return out


SENSORS: list[_SensorSpec] = [
    _SensorSpec(
        key="volume_percent",
        name="Volume",
        icon="mdi:volume-high",
        value=lambda d: int((d.volume_level or 0) * 100),
        attrs=lambda d: {"max_volume": d.max_volume},
    ),
    _SensorSpec(
        key="input_source",
        name="Input Source",
        icon="mdi:video-input-hdmi",
        value=lambda d: d.input_source,
        attrs=lambda d: {"supported_input_sources": d.supported_input_sources},
    ),
    _SensorSpec(
        key="thing_status",
        name="Thing Status",
        icon="mdi:information",
        value=lambda d: d._attr("status"),
        attrs=lambda d: {"updated_time": d._attr("updatedTime")},
    ),
    _SensorSpec(
        key="sound_from_mode",
        name="Sound From Mode",
        icon="mdi:speaker",
        value=lambda d: d._attr("mode"),
        attrs=lambda d: {"detailName": d._attr("detailName")},
        enabled_by_default=False,
    ),
    _SensorSpec(
        key="ocf_model",
        name="Model",
        icon="mdi:identifier",
        value=lambda d: d.model,
        attrs=lambda d: _attrs_from(
            d,
            [
                "mnmo",  # model (ex: HW-Q990D)
                "mnfv",  # firmware
                "mnos",  # OS (ex: Tizen)
                "mnpv",  # OS version
                "vid",
                "dmv",
                "icv",
                "mndt",
            ],
        ),
    ),
    _SensorSpec(
        key="supported_features",
        name="Supported Features",
        icon="mdi:feature-search",
        value=lambda d: d._attr("wifiUpdateSupport"),
        attrs=lambda d: _attrs_from(
            d,
            [
                "wifiUpdateSupport",
                "artSupported",
                "executableServiceList",
                "imeAdvSupported",
                "mediaOutputSupported",
                "mobileCamSupported",
                "remotelessSupported",
            ],
        ),
        enabled_by_default=False,
    ),
    _SensorSpec(
        key="wifi_configuration",
        name="WiFi Configuration",
        icon="mdi:wifi-cog",
        value=lambda d: d._attr("autoReconnection"),
        attrs=lambda d: _attrs_from(
            d,
            [
                "autoReconnection",
                "supportedAuthType",
                "supportedWiFiFreq",
                "protocolType",
                "minVersion",
            ],
        ),
        enabled_by_default=False,
    ),
    _SensorSpec(
        key="diagnostics_information",
        name="Diagnostics Information",
        icon="mdi:tools",
        value=lambda d: d._attr("endpoint"),
        attrs=lambda d: _attrs_from(
            d,
            [
                "endpoint",
                "dumpType",
                "logType",
                "protocolType",
                "setupId",
                "mnId",
                "tsId",
                "minVersion",
            ],
        ),
        enabled_by_default=False,
    ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_data = hass.data[DOMAIN]
    entities: list[SoundbarSensor] = []

    for key in domain_data.devices:
        device_config: DeviceConfig = domain_data.devices[key]
        device = device_config.device
        coordinator = device_config.coordinator
        if device.device_id != config_entry.data.get(CONF_ENTRY_DEVICE_ID):
            continue
        for spec in SENSORS:
            entities.append(SoundbarSensor(coordinator, spec))

    async_add_entities(entities)
    return True


class SoundbarSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, spec: _SensorSpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        dev: SoundbarDevice = coordinator.data

        self._attr_unique_id = f"{dev.device_id}_{spec.key}"
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        self._attr_entity_registry_enabled_default = spec.enabled_by_default
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev.device_id)},
            name=dev.device_name,
            manufacturer=dev.manufacturer,
            model=dev.model,
            sw_version=dev.firmware_version,
        )

    @property
    def native_value(self):
        dev: SoundbarDevice = self.coordinator.data
        return self._spec.value(dev)

    @property
    def extra_state_attributes(self):
        if not self._spec.attrs:
            return None
        dev: SoundbarDevice = self.coordinator.data
        return self._spec.attrs(dev)
