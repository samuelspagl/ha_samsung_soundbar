from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


API_BASE = "https://api.smartthings.com/v1"


class SmartThingsApi:
    def __init__(self, hass, token: str):
        self._hass = hass
        self._token = token
        self._session = async_get_clientsession(hass)

    @property
    def token(self) -> str:
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    async def get(self, path: str) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        async with self._session.get(url, headers=self._headers()) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        async with self._session.post(url, headers=self._headers() | {"Content-Type": "application/json"}, json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_device(self, device_id: str) -> dict[str, Any]:
        return await self.get(f"/devices/{device_id}")

    async def get_status(self, device_id: str) -> dict[str, Any]:
        return await self.get(f"/devices/{device_id}/status")

    async def send_commands(self, device_id: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
        return await self.post(f"/devices/{device_id}/commands", {"commands": commands})
