from dataclasses import dataclass

from .api_extension.SoundbarDevice import SoundbarDevice
from .coordinator import SoundbarCoordinator
from .smartthings_api import SmartThingsApi


@dataclass
class DeviceConfig:
    config: dict
    device: SoundbarDevice
    coordinator: SoundbarCoordinator


@dataclass
class SoundbarConfig:
    api: SmartThingsApi
    devices: dict
