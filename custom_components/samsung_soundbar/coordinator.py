from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_extension.SoundbarDevice import SoundbarDevice
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


DEFAULT_UPDATE_INTERVAL = timedelta(seconds=10)


class SoundbarCoordinator(DataUpdateCoordinator[SoundbarDevice]):
    def __init__(self, hass: HomeAssistant, device: SoundbarDevice) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device.device_id}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self._device = device

    async def _async_update_data(self) -> SoundbarDevice:
        try:
            await self._device.update()
            return self._device
        except Exception as err:
            raise UpdateFailed(str(err)) from err

