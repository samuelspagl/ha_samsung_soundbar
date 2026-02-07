from dataclasses import dataclass

from pysmartthings import SmartThings

from .api_extension.SoundbarDevice import SoundbarDevice
from .coordinator import SoundbarCoordinator


@dataclass
class DeviceConfig:
    config: dict
    device: SoundbarDevice
    coordinator: SoundbarCoordinator


@dataclass
class SoundbarConfig:
    api: SmartThings
    devices: dict
