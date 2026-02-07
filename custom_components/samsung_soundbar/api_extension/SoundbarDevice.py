from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from typing import Any

from ..const import DOMAIN
from ..smartthings_api import SmartThingsApi
from .const import RearSpeakerMode, SpeakerIdentifier

_LOGGER = logging.getLogger(__name__)


class SoundbarDevice:
    """
    SmartThings Soundbar wrapper using the raw SmartThings REST API.

    This avoids depending on `pysmartthings`, which has had breaking API/exports
    across versions (and caused config flow/runtime import errors).
    """

    def __init__(
        self,
        api_key: str,
        api: SmartThingsApi,
        *,
        device_id: str,
        max_volume: int,
        device_name: str,
        enable_eq: bool = False,
        enable_soundmode: bool = False,
        enable_advanced_audio: bool = False,
        enable_woofer: bool = False,
    ) -> None:
        self._api = api
        self._api_key = api_key
        self._device_id = device_id

        self.__device_name = device_name
        self.__max_volume = int(max_volume)

        # Feature flags (UI toggles)
        self.__enable_eq = bool(enable_eq)
        self.__enable_soundmode = bool(enable_soundmode)
        self.__enable_advanced_audio = bool(enable_advanced_audio)
        self.__enable_woofer = bool(enable_woofer)

        # Cached REST payloads
        self._device: dict[str, Any] | None = None
        self._status: dict[str, Any] | None = None
        self._main: dict[str, Any] = {}

        # Derived state
        self.__supported_soundmodes: list[str] = []
        self.__active_soundmode: str | None = None
        self.__woofer_level: int | None = None
        self.__woofer_connection: str | None = None
        self.__active_eq_preset: str | None = None
        self.__supported_eq_presets: list[str] = []
        self.__eq_action: Any = None
        self.__eq_bands: Any = None
        self.__night_mode: int | None = None
        self.__bass_mode: int | None = None
        self.__voice_amplifier: int | None = None

        # Media metadata (often not available on OCF models; keep optional)
        self.__media_title: str | None = None
        self.__media_artist: str | None = None
        self.__media_cover_url: str | None = None
        self.__media_cover_url_update_time: dt.datetime | None = None

        # execute/status is rate limited and for some OCF models returns null permanently.
        self.__execute_status_supported: bool | None = None

    # ------------ REST helpers ------------

    async def command(self, capability: str, command: str, arguments: list[Any] | None = None) -> None:
        cmd: dict[str, Any] = {
            "component": "main",
            "capability": capability,
            "command": command,
        }
        if arguments is not None:
            cmd["arguments"] = arguments
        await self._api.send_commands(self._device_id, [cmd])

    def _cap(self, capability: str) -> dict[str, Any]:
        v = self._main.get(capability)
        return v if isinstance(v, dict) else {}

    def _cap_attr(self, capability: str, attr: str) -> Any:
        cap = self._cap(capability)
        node = cap.get(attr)
        if isinstance(node, dict):
            return node.get("value")
        return None

    def _attr(self, name: str) -> Any:
        # Best-effort search across all capabilities in main.
        for cap in self._main.values():
            if not isinstance(cap, dict):
                continue
            node = cap.get(name)
            if isinstance(node, dict) and "value" in node:
                return node.get("value")
        return None

    async def update(self) -> None:
        self._device = await self._api.get_device(self._device_id)
        self._status = await self._api.get_status(self._device_id)
        self._main = (
            (self._status.get("components") or {}).get("main") or {}
            if isinstance(self._status, dict)
            else {}
        )

        # Cache fields that we expose as properties
        if self.__enable_soundmode:
            await self._update_soundmode()
        if self.__enable_advanced_audio:
            await self._update_advanced_audio()
        if self.__enable_woofer:
            await self._update_woofer()
        if self.__enable_eq:
            await self._update_equalizer()

    # ------------ Device information ----------

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def device_name(self) -> str:
        return self.__device_name

    @property
    def manufacturer(self) -> str | None:
        # Prefer OCF, fallback to /devices
        return self._attr("mnmn") or (self._device or {}).get("manufacturerName")

    @property
    def model(self) -> str | None:
        # OCF model (mnmo) is typically set (ex: HW-Q990D)
        return self._attr("mnmo") or (self._device or {}).get("model")

    @property
    def firmware_version(self) -> str | None:
        return self._attr("mnfv")

    # ------------ On / Off ------------

    @property
    def state(self) -> str:
        sw = self._cap_attr("switch", "switch")
        is_on = (sw == "on") or (sw is True)
        if not is_on:
            return "off"

        # thingStatus is often \"Idle\" when on.
        ts = self._cap_attr("samsungvd.thingStatus", "status")
        if isinstance(ts, str) and ts.lower() in ("playing", "paused"):
            return ts.lower()

        return "on"

    async def switch_off(self) -> None:
        await self.command("switch", "off", [])

    async def switch_on(self) -> None:
        await self.command("switch", "on", [])

    # ------------ Volume / Mute ------------

    @property
    def max_volume(self) -> int:
        return self.__max_volume

    @property
    def volume_level(self) -> float:
        vol = self._cap_attr("audioVolume", "volume")
        try:
            vol_int = int(vol)
        except Exception:
            vol_int = 0
        if vol_int > self.__max_volume:
            return 1.0
        return vol_int / float(self.__max_volume)

    @property
    def volume_muted(self) -> bool:
        return bool(self._cap_attr("audioMute", "mute"))

    async def set_volume(self, volume: float) -> None:
        # volume is 0..1 from HA
        v = int(float(volume) * self.__max_volume)
        v = max(0, min(self.__max_volume, v))
        await self.command("audioVolume", "setVolume", [v])

    async def mute_volume(self, mute: bool) -> None:
        await self.command("audioMute", "mute" if mute else "unmute", [])

    async def volume_up(self) -> None:
        await self.command("audioVolume", "volumeUp", [])

    async def volume_down(self) -> None:
        await self.command("audioVolume", "volumeDown", [])

    # ------------ Input Sources ------------

    @property
    def input_source(self) -> str | None:
        return self._cap_attr("samsungvd.audioInputSource", "inputSource")

    @property
    def supported_input_sources(self) -> list[str]:
        sources = self._cap_attr("samsungvd.audioInputSource", "supportedInputSources")
        return list(sources) if isinstance(sources, list) else []

    async def select_source(self, source: str) -> None:
        sources = self.supported_input_sources
        if not sources:
            raise ValueError("No supported input sources reported by SmartThings")
        if source not in sources:
            raise ValueError(f"Unsupported source: {source}")
        current = self.input_source
        if current == source:
            return

        cur_idx = sources.index(current) if current in sources else 0
        tgt_idx = sources.index(source)
        steps = (tgt_idx - cur_idx) % len(sources)
        for _ in range(steps):
            await self.command("samsungvd.audioInputSource", "setNextInputSource", [])
            await asyncio.sleep(0.6)
            await self._refresh_status_only()

    async def _refresh_status_only(self) -> None:
        self._status = await self._api.get_status(self._device_id)
        self._main = (
            (self._status.get("components") or {}).get("main") or {}
            if isinstance(self._status, dict)
            else {}
        )

    # ------------ Media metadata (limited) ------------

    @property
    def media_title(self) -> str | None:
        return self.__media_title

    @property
    def media_artist(self) -> str | None:
        return self.__media_artist

    @property
    def media_coverart_url(self) -> str | None:
        return self.__media_cover_url

    @property
    def media_coverart_updated(self) -> dt.datetime | None:
        return self.__media_cover_url_update_time

    @property
    def media_duration(self) -> int | None:
        return None

    @property
    def media_position(self) -> int | None:
        return None

    @property
    def media_app_name(self) -> str | None:
        return self._cap_attr("samsungvd.soundFrom", "detailName")

    # Media playback is not exposed for many OCF soundbars via SmartThings.
    # Keep stubs so entity code can call them safely if ever enabled.

    async def media_play(self) -> None:
        raise NotImplementedError("Media playback is not supported by this device via SmartThings")

    async def media_pause(self) -> None:
        raise NotImplementedError("Media playback is not supported by this device via SmartThings")

    async def media_stop(self) -> None:
        raise NotImplementedError("Media playback is not supported by this device via SmartThings")

    async def media_next_track(self) -> None:
        raise NotImplementedError("Media playback is not supported by this device via SmartThings")

    async def media_previous_track(self) -> None:
        raise NotImplementedError("Media playback is not supported by this device via SmartThings")

    # ------------ Execute-based features (may not work on OCF models) ------------

    async def get_execute_status(self) -> dict[str, Any]:
        # execute status is also exposed as /status under execute.data.value
        data = self._cap_attr("execute", "data")
        if isinstance(data, dict):
            payload = (data.get("payload") or {}) if isinstance(data.get("payload"), dict) else {}
            self.__execute_status_supported = bool(payload)
            return payload

        # Fall back to dedicated endpoint (often returns null on OCF models)
        try:
            resp = await self._api.get(f"/devices/{self._device_id}/components/main/capabilities/execute/status")
        except Exception:
            self.__execute_status_supported = False
            return {}
        if not isinstance(resp, dict) or "error" in resp:
            self.__execute_status_supported = False
            return {}
        value = ((resp.get("data") or {}).get("value"))
        if not isinstance(value, dict):
            self.__execute_status_supported = False
            return {}
        payload = value.get("payload")
        if isinstance(payload, dict):
            self.__execute_status_supported = True
            return payload
        self.__execute_status_supported = False
        return {}

    async def set_custom_execution_data(self, href: str, property: str, value: Any) -> None:
        # execute.execute(command, args)
        await self.command("execute", "execute", [href, {property: value}])

    async def execute_set_raw(self, href: str, prop: str, value: Any) -> None:
        await self.set_custom_execution_data(href=href, property=prop, value=value)

    async def ocf_post(self, href: str, value: dict[str, Any]) -> None:
        await self.command("ocf", "postOcfCommand", [href, value])

    # The following helpers keep old service names; on OCF models they may no-op if status doesn't exist.

    async def _update_soundmode(self) -> None:
        if self.__execute_status_supported is False:
            return
        await self.command("execute", "execute", ["/sec/networkaudio/soundmode"])
        await asyncio.sleep(0.5)
        payload = await self.get_execute_status()
        self.__supported_soundmodes = list(payload.get("x.com.samsung.networkaudio.supportedSoundmode") or [])
        self.__active_soundmode = payload.get("x.com.samsung.networkaudio.soundmode")

    async def _update_woofer(self) -> None:
        if self.__execute_status_supported is False:
            return
        await self.command("execute", "execute", ["/sec/networkaudio/woofer"])
        await asyncio.sleep(0.5)
        payload = await self.get_execute_status()
        self.__woofer_level = payload.get("x.com.samsung.networkaudio.woofer")
        self.__woofer_connection = payload.get("x.com.samsung.networkaudio.connection")

    async def _update_equalizer(self) -> None:
        if self.__execute_status_supported is False:
            return
        await self.command("execute", "execute", ["/sec/networkaudio/eq"])
        await asyncio.sleep(0.5)
        payload = await self.get_execute_status()
        self.__active_eq_preset = payload.get("x.com.samsung.networkaudio.EQname")
        self.__supported_eq_presets = list(payload.get("x.com.samsung.networkaudio.supportedList") or [])
        self.__eq_action = payload.get("x.com.samsung.networkaudio.action")
        self.__eq_bands = payload.get("x.com.samsung.networkaudio.EQband")

    async def _update_advanced_audio(self) -> None:
        if self.__execute_status_supported is False:
            return
        await self.command("execute", "execute", ["/sec/networkaudio/advancedaudio"])
        await asyncio.sleep(0.5)
        payload = await self.get_execute_status()
        self.__night_mode = payload.get("x.com.samsung.networkaudio.nightmode")
        self.__bass_mode = payload.get("x.com.samsung.networkaudio.bassboost")
        self.__voice_amplifier = payload.get("x.com.samsung.networkaudio.voiceamplifier")

    # ------------ Sound mode (execute-based) ------------

    @property
    def sound_mode(self) -> str | None:
        return self.__active_soundmode

    @property
    def supported_soundmodes(self) -> list[str]:
        return self.__supported_soundmodes

    async def select_sound_mode(self, sound_mode: str) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/soundmode",
            property="x.com.samsung.networkaudio.soundmode",
            value=sound_mode,
        )

    # ------------ Advanced audio toggles (execute-based) ------------

    @property
    def night_mode(self) -> bool:
        return bool(self.__night_mode == 1)

    async def set_night_mode(self, value: bool) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/advancedaudio",
            property="x.com.samsung.networkaudio.nightmode",
            value=1 if value else 0,
        )

    @property
    def bass_mode(self) -> bool:
        return bool(self.__bass_mode == 1)

    async def set_bass_mode(self, value: bool) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/advancedaudio",
            property="x.com.samsung.networkaudio.bassboost",
            value=1 if value else 0,
        )

    @property
    def voice_amplifier(self) -> bool:
        return bool(self.__voice_amplifier == 1)

    async def set_voice_amplifier(self, value: bool) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/advancedaudio",
            property="x.com.samsung.networkaudio.voiceamplifier",
            value=1 if value else 0,
        )

    # ------------ Equalizer (execute-based) ------------

    @property
    def active_equalizer_preset(self) -> str | None:
        return self.__active_eq_preset

    @property
    def supported_equalizer_presets(self) -> list[str]:
        return self.__supported_eq_presets

    @property
    def equalizer_action(self) -> Any:
        return self.__eq_action

    @property
    def equalizer_bands(self) -> Any:
        return self.__eq_bands

    async def set_equalizer_preset(self, preset: str) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/eq",
            property="x.com.samsung.networkaudio.EQname",
            value=preset,
        )

    # ------------ Woofer (execute-based) ------------

    @property
    def woofer_level(self) -> int | None:
        return self.__woofer_level

    @property
    def woofer_connection(self) -> str | None:
        return self.__woofer_connection

    async def set_woofer(self, level: int) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/woofer",
            property="x.com.samsung.networkaudio.woofer",
            value=level,
        )

    # ------------ Speaker level (execute-based) ------------

    async def set_speaker_level(self, speaker: SpeakerIdentifier, level: int) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/channelVolume",
            property="x.com.samsung.networkaudio.channelVolume",
            value=[{"name": speaker.value, "value": level}],
        )

    async def set_rear_speaker_mode(self, mode: RearSpeakerMode) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/surroundspeaker",
            property="x.com.samsung.networkaudio.currentRearPosition",
            value=mode.value,
        )

    async def set_active_voice_amplifier(self, enabled: bool) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/activeVoiceAmplifier",
            property="x.com.samsung.networkaudio.activeVoiceAmplifier",
            value=1 if enabled else 0,
        )

    async def set_space_fit_sound(self, enabled: bool) -> None:
        await self.set_custom_execution_data(
            href="/sec/networkaudio/spacefitSound",
            property="x.com.samsung.networkaudio.spacefitSound",
            value=1 if enabled else 0,
        )

    # ------------ Audio notifications (native capability) ------------

    async def play_track(self, uri: str, level: int | None = None) -> None:
        args = [uri] if level is None else [uri, level]
        await self.command("audioNotification", "playTrack", args)

    async def play_track_and_restore(self, uri: str, level: int | None = None) -> None:
        args = [uri] if level is None else [uri, level]
        await self.command("audioNotification", "playTrackAndRestore", args)

    async def play_track_and_resume(self, uri: str, level: int | None = None) -> None:
        args = [uri] if level is None else [uri, level]
        await self.command("audioNotification", "playTrackAndResume", args)

    # ------------ Read-only debug blob ------------

    @property
    def retrieve_data(self) -> dict[str, Any]:
        return {
            "device": self._device,
            "status": self._status,
        }
