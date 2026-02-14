import asyncio
import datetime
import json
import logging
import re
from typing import Any
from urllib.parse import quote

from pysmartthings import Capability, Command, Device, SmartThings

from .const import RearSpeakerMode, SpeakerIdentifier

DOMAIN = "soundbar"
log = logging.getLogger(__name__)


class SoundbarDevice:
    def __init__(
        self,
        device: Device,
        smartthings: SmartThings | None = None,
        session: Any | None = None,
        max_volume: int = 100,
        device_name: str | None = None,
        enable_eq: bool = False,
        enable_soundmode: bool = False,
        enable_advanced_audio: bool = False,
        enable_woofer: bool = False,
    ):
        self.device = device
        self._device_id = self.device.device_id

        self.__smartthings = smartthings or getattr(self.device, "_api", None)
        if self.__smartthings is None:
            raise ValueError(
                "SoundbarDevice requires a SmartThings client. "
                "Pass `smartthings=SmartThings(...)` when using pysmartthings>=3.5."
            )
        if not hasattr(self.__smartthings, "get_device_status") or not hasattr(
            self.__smartthings, "execute_device_command"
        ):
            raise TypeError(
                "Unsupported SmartThings client object. "
                "Expected methods `get_device_status` and `execute_device_command`."
            )

        self.__session = session
        self.__device_name = device_name or self.device.label or self.device.name
        self.__status_data: dict[str, Any] = {}

        self.__enable_soundmode = enable_soundmode
        self.__supported_soundmodes = []
        self.__active_soundmode = ""

        self.__enable_woofer = enable_woofer
        self.__woofer_level = 0
        self.__woofer_connection = ""

        self.__enable_eq = enable_eq
        self.__active_eq_preset = ""
        self.__supported_eq_presets = []
        self.__eq_action = ""
        self.__eq_bands = []

        self.__enable_advanced_audio = enable_advanced_audio
        self.__voice_amplifier = 0
        self.__night_mode = 0
        self.__bass_mode = 0

        self.__media_title = ""
        self.__media_artist = ""
        self.__media_cover_url = ""
        self.__media_cover_url_update_time: datetime.datetime | None = None
        self.__old_media_title = ""

        self.__max_volume = max_volume
        self.__status_retry_at: datetime.datetime | None = None
        self.__execute_retry_at: datetime.datetime | None = None

    async def update(self):
        now = datetime.datetime.now()
        if self.__status_retry_at and now < self.__status_retry_at:
            return

        try:
            raw_status = await self.__smartthings.get_raw_device_status(self._device_id)
        except Exception as raw_exc:  # pylint: disable=broad-except
            log.warning(
                "[%s] get_raw_device_status failed for %s: %s",
                DOMAIN,
                self._device_id,
                raw_exc,
            )
            self.__status_retry_at = datetime.datetime.now() + datetime.timedelta(seconds=3)
            return

        if isinstance(raw_status, dict) and isinstance(raw_status.get("components"), dict):
            self.__status_data = raw_status["components"]
            self.__status_retry_at = None
        else:
            retry_delay = self._get_retry_delay_seconds(raw_status)
            if retry_delay is not None:
                self.__status_retry_at = datetime.datetime.now() + datetime.timedelta(
                    seconds=retry_delay
                )
            return

        await self._update_media()

        if self.__enable_soundmode:
            await self._update_soundmode()
        if self.__enable_advanced_audio:
            await self._update_advanced_audio()
        if self.__enable_woofer:
            await self._update_woofer()
        if self.__enable_eq:
            await self._update_equalizer()

    def _extract_too_many_requests_delay(self, error: Any) -> float | None:
        if not isinstance(error, dict):
            return None
        if error.get("code") != "TooManyRequestError":
            return None

        details = error.get("details")
        if not isinstance(details, list):
            return 2.0

        for detail in details:
            if not isinstance(detail, dict):
                continue
            message = detail.get("message")
            if not isinstance(message, str):
                continue
            match = re.search(r"retry in (\d+) millis", message)
            if match:
                try:
                    return max(1.0, int(match.group(1)) / 1000.0)
                except ValueError:
                    return 2.0
        return 2.0

    def _get_retry_delay_seconds(self, raw_status: Any) -> float | None:
        if not isinstance(raw_status, dict):
            return None
        return self._extract_too_many_requests_delay(raw_status.get("error"))

    async def _wait_for_execute_payload(
        self,
        required_key: str,
        timeout: float = 30.0,
        interval: float = 0.5,
    ) -> dict[str, Any] | None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            payload = await self.get_execute_status()
            if required_key in payload:
                return payload
            await asyncio.sleep(interval)
        return None

    def _get_status_value(
        self,
        capability: str,
        attribute: str,
        component: str = "main",
        default: Any = None,
    ) -> Any:
        component_status = self.__status_data.get(component, {})
        capability_status = component_status.get(capability)
        if not isinstance(capability_status, dict):
            return default

        status = capability_status.get(attribute)
        if status is None:
            return default

        if isinstance(status, dict):
            value = status.get("value")
        else:
            value = getattr(status, "value", None)
        if value is None:
            return default
        return value

    def _get_status_record(
        self,
        capability: str,
        attribute: str,
        component: str = "main",
    ) -> dict[str, Any] | None:
        component_status = self.__status_data.get(component, {})
        if not isinstance(component_status, dict):
            return None
        capability_status = component_status.get(capability)
        if not isinstance(capability_status, dict):
            return None
        status = capability_status.get(attribute)
        if status is None:
            return None

        if isinstance(status, dict):
            return status

        record: dict[str, Any] = {}
        for key in ("value", "unit", "timestamp", "data"):
            value = getattr(status, key, None)
            if value is not None:
                record[key] = value
        return record or None

    def _get_status_timestamp(
        self,
        capability: str,
        attribute: str,
        component: str = "main",
    ) -> str | None:
        record = self._get_status_record(capability, attribute, component=component)
        if not isinstance(record, dict):
            return None
        timestamp = record.get("timestamp")
        if isinstance(timestamp, datetime.datetime):
            return timestamp.isoformat()
        if isinstance(timestamp, str):
            return timestamp
        return None

    def _find_attribute_value(
        self, attribute: str, component: str = "main", default: Any = None
    ) -> Any:
        component_status = self.__status_data.get(component, {})
        if not isinstance(component_status, dict):
            return default

        for capability_status in component_status.values():
            if not isinstance(capability_status, dict):
                continue
            status = capability_status.get(attribute)
            if status is None:
                continue
            if isinstance(status, dict):
                value = status.get("value")
            else:
                value = getattr(status, "value", None)
            if value is not None:
                return value

        return default

    def _get_first_status_value(
        self,
        capabilities: tuple[str, ...],
        attribute: str,
        component: str = "main",
        default: Any = None,
    ) -> Any:
        for capability in capabilities:
            value = self._get_status_value(
                capability=capability,
                attribute=attribute,
                component=component,
                default=None,
            )
            if value is None:
                continue
            if isinstance(value, str) and value == "":
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            return value
        return default

    async def _update_media(self):
        audio_track = self._get_status_value(
            Capability.AUDIO_TRACK_DATA, "audioTrackData", default={}
        )
        if not isinstance(audio_track, dict):
            return

        self.__media_artist = audio_track.get("artist", "")
        self.__media_title = audio_track.get("title", "")
        if self.__media_title != self.__old_media_title:
            self.__old_media_title = self.__media_title
            self.__media_cover_url_update_time = datetime.datetime.now()
            self.__media_cover_url = await self.get_song_title_artwork(
                self.__media_artist, self.__media_title
            )

    async def _update_soundmode(self):
        await self.update_execution_data(["/sec/networkaudio/soundmode"])
        payload = await self._wait_for_execute_payload(
            required_key="x.com.samsung.networkaudio.supportedSoundmode",
            timeout=15.0,
            interval=1.0,
        )
        if payload is None:
            log.error(f"[{DOMAIN}] Error: _update_soundmode timed out waiting for execute payload")
            return

        self.__supported_soundmodes = payload[
            "x.com.samsung.networkaudio.supportedSoundmode"
        ]
        self.__active_soundmode = payload["x.com.samsung.networkaudio.soundmode"]

    async def _update_woofer(self):
        await self.update_execution_data(["/sec/networkaudio/woofer"])
        payload = await self._wait_for_execute_payload(
            required_key="x.com.samsung.networkaudio.woofer",
            timeout=15.0,
            interval=1,
        )
        if payload is None:
            log.error(f"[{DOMAIN}] Error: _update_woofer timed out waiting for execute payload")
            return
        self.__woofer_level = payload["x.com.samsung.networkaudio.woofer"]
        self.__woofer_connection = payload["x.com.samsung.networkaudio.connection"]

    async def _update_equalizer(self):
        await self.update_execution_data(["/sec/networkaudio/eq"])
        payload = await self._wait_for_execute_payload(
            required_key="x.com.samsung.networkaudio.EQname",
            timeout=15.0,
            interval=1,
        )
        if payload is None:
            log.error(f"[{DOMAIN}] Error: _update_equalizer timed out waiting for execute payload")
            return
        self.__active_eq_preset = payload["x.com.samsung.networkaudio.EQname"]
        self.__supported_eq_presets = payload["x.com.samsung.networkaudio.supportedList"]
        self.__eq_action = payload["x.com.samsung.networkaudio.action"]
        self.__eq_bands = payload["x.com.samsung.networkaudio.EQband"]

    async def _update_advanced_audio(self):
        await self.update_execution_data(["/sec/networkaudio/advancedaudio"])
        payload = await self._wait_for_execute_payload(
            required_key="x.com.samsung.networkaudio.nightmode",
            timeout=15.0,
            interval=1.0,
        )
        if payload is None:
            log.error(
                f"[{DOMAIN}] Error: _update_advanced_audio timed out waiting for execute payload"
            )
            return

        self.__night_mode = payload["x.com.samsung.networkaudio.nightmode"]
        self.__bass_mode = payload["x.com.samsung.networkaudio.bassboost"]
        self.__voice_amplifier = payload["x.com.samsung.networkaudio.voiceamplifier"]

    @property
    def status(self):
        return self.__status_data

    # ------------ DEVICE INFORMATION ----------

    @property
    def manufacturer(self):
        if self.device.ocf and self.device.ocf.manufacturer_name:
            return self.device.ocf.manufacturer_name
        return self._find_attribute_value("manufacturerName")

    @property
    def model(self):
        if self.device.ocf and self.device.ocf.model_number:
            return self.device.ocf.model_number
        return self._find_attribute_value("modelNumber")

    @property
    def firmware_version(self):
        if self.device.ocf and self.device.ocf.firmware_version:
            return self.device.ocf.firmware_version
        if self.device.hub:
            return self.device.hub.firmware_version
        return self._find_attribute_value("firmwareVersion")

    @property
    def device_id(self):
        return self.device.device_id

    @property
    def device_name(self):
        return self.__device_name

    # ------------ ON / OFF ------------

    @property
    def state(self) -> str:
        switch_state = self._get_status_value(Capability.SWITCH, "switch", default="off")
        if isinstance(switch_state, str):
            is_on = switch_state.lower() == "on"
        else:
            is_on = bool(switch_state)

        if not is_on:
            return "off"

        playback_status = self._get_status_value(
            Capability.MEDIA_PLAYBACK, "playbackStatus", default=""
        )
        if playback_status == "playing":
            return "playing"
        if playback_status == "paused":
            return "paused"
        return "on"

    async def switch_off(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.SWITCH, Command.OFF
        )

    async def switch_on(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.SWITCH, Command.ON
        )

    # ------------ VOLUME --------------

    @property
    def volume_level(self) -> float:
        vol = self._get_status_value(Capability.AUDIO_VOLUME, "volume", default=0)
        try:
            vol_int = int(vol)
        except (TypeError, ValueError):
            return 0.0

        if self.__max_volume <= 0:
            return 0.0
        if vol_int > self.__max_volume:
            return 1.0
        return vol_int / self.__max_volume

    @property
    def volume_muted(self) -> bool:
        mute = self._get_status_value(Capability.AUDIO_MUTE, "mute", default=False)
        if isinstance(mute, str):
            return mute.lower() in {"muted", "mute", "on", "true", "1"}
        return bool(mute)

    async def set_volume(self, volume: float):
        """
        Sets the volume to a certain level.
        This respects the max volume and hovers between
        :param volume: between 0 and 1
        """
        target = int(volume * self.__max_volume)
        target = max(0, min(target, self.__max_volume))
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.AUDIO_VOLUME, Command.SET_VOLUME, argument=target
        )

    async def mute_volume(self, mute: bool):
        await self.__smartthings.execute_device_command(
            self._device_id,
            Capability.AUDIO_MUTE,
            Command.MUTE if mute else Command.UNMUTE,
        )

    async def volume_up(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.AUDIO_VOLUME, Command.VOLUME_UP
        )

    async def volume_down(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.AUDIO_VOLUME, Command.VOLUME_DOWN
        )

    # ------------ WOOFER LEVEL -------------

    @property
    def woofer_level(self) -> int:
        return self.__woofer_level

    @property
    def woofer_connection(self) -> str:
        return self.__woofer_connection

    async def set_woofer(self, level: int):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/woofer",
            property="x.com.samsung.networkaudio.woofer",
            value=level,
        )
        self.__woofer_level = level

    # ------------ INPUT SOURCE -------------

    @property
    def input_source(self):
        source = self._get_first_status_value(
            (
                Capability.SAMSUNG_VD_AUDIO_INPUT_SOURCE,
                Capability.SAMSUNG_VD_MEDIA_INPUT_SOURCE,
                Capability.MEDIA_INPUT_SOURCE,
            ),
            "inputSource",
            default=None,
        )
        if source is not None:
            return source
        if self.media_app_name in ("AirPlay", "Spotify"):
            return "wifi"
        return None

    @property
    def supported_input_sources(self):
        return self._get_first_status_value(
            (
                Capability.SAMSUNG_VD_AUDIO_INPUT_SOURCE,
                Capability.SAMSUNG_VD_MEDIA_INPUT_SOURCE,
                Capability.MEDIA_INPUT_SOURCE,
            ),
            "supportedInputSources",
            default=[],
        )

    async def select_source(self, source: str):
        main_status = self.__status_data.get("main", {})
        if isinstance(main_status, dict):
            if Capability.SAMSUNG_VD_MEDIA_INPUT_SOURCE in main_status:
                await self.__smartthings.execute_device_command(
                    self._device_id,
                    Capability.SAMSUNG_VD_MEDIA_INPUT_SOURCE,
                    Command.SET_INPUT_SOURCE,
                    argument=source,
                )
                return
            if Capability.MEDIA_INPUT_SOURCE in main_status:
                await self.__smartthings.execute_device_command(
                    self._device_id,
                    Capability.MEDIA_INPUT_SOURCE,
                    Command.SET_INPUT_SOURCE,
                    argument=source,
                )
                return
            if Capability.SAMSUNG_VD_AUDIO_INPUT_SOURCE in main_status:
                await self.__smartthings.execute_device_command(
                    self._device_id,
                    Capability.SAMSUNG_VD_AUDIO_INPUT_SOURCE,
                    Command.SET_NEXT_INPUT_SOURCE,
                )
                return

        await self.__smartthings.execute_device_command(
            self._device_id,
            Capability.MEDIA_INPUT_SOURCE,
            Command.SET_INPUT_SOURCE,
            argument=source,
        )

    # ------------- SOUND MODE --------------
    @property
    def sound_mode(self):
        return self.__active_soundmode

    @property
    def supported_soundmodes(self):
        return self.__supported_soundmodes

    async def select_sound_mode(self, sound_mode: str):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/soundmode",
            property="x.com.samsung.networkaudio.soundmode",
            value=sound_mode,
        )

    # ------------- ADVANCED AUDIO ---------------

    @property
    def night_mode(self) -> bool:
        return self.__night_mode == 1

    async def set_night_mode(self, value: bool):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/advancedaudio",
            property="x.com.samsung.networkaudio.nightmode",
            value=1 if value else 0,
        )
        self.__night_mode = 1 if value else 0

    @property
    def bass_mode(self) -> bool:
        return self.__bass_mode == 1

    async def set_bass_mode(self, value: bool):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/advancedaudio",
            property="x.com.samsung.networkaudio.bassboost",
            value=1 if value else 0,
        )
        self.__bass_mode = 1 if value else 0

    @property
    def voice_amplifier(self) -> bool:
        return self.__voice_amplifier == 1

    async def set_voice_amplifier(self, value: bool):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/advancedaudio",
            property="x.com.samsung.networkaudio.voiceamplifier",
            value=1 if value else 0,
        )
        self.__voice_amplifier = 1 if value else 0

    # ------------ EQUALIZER --------------

    @property
    def active_equalizer_preset(self):
        return self.__active_eq_preset

    @property
    def supported_equalizer_presets(self):
        return self.__supported_eq_presets

    @property
    def equalizer_action(self):
        return self.__eq_action

    @property
    def equalizer_bands(self):
        return self.__eq_bands

    async def set_equalizer_preset(self, preset: str):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/eq",
            property="x.com.samsung.networkaudio.EQname",
            value=preset,
        )

    # ------------- MEDIA ----------------
    @property
    def media_title(self):
        return self.__media_title

    @property
    def media_artist(self):
        return self.__media_artist

    @property
    def media_coverart_url(self):
        return self.__media_cover_url

    @property
    def media_duration(self) -> int | None:
        value = self._get_status_value(Capability.MEDIA_PLAYBACK, "totalTime")
        if value is None:
            value = self._find_attribute_value("totalTime")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @property
    def media_position(self) -> int | None:
        value = self._get_status_value(Capability.MEDIA_PLAYBACK, "elapsedTime")
        if value is None:
            value = self._find_attribute_value("elapsedTime")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def media_play(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.MEDIA_PLAYBACK, Command.PLAY
        )

    async def media_pause(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.MEDIA_PLAYBACK, Command.PAUSE
        )

    async def media_stop(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.MEDIA_PLAYBACK, Command.STOP
        )

    async def media_next_track(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.MEDIA_PLAYBACK, Command.FAST_FORWARD
        )

    async def media_previous_track(self):
        await self.__smartthings.execute_device_command(
            self._device_id, Capability.MEDIA_PLAYBACK, Command.REWIND
        )

    @property
    def media_app_name(self):
        return self._find_attribute_value("detailName")

    @property
    def media_coverart_updated(self) -> datetime.datetime | None:
        return self.__media_cover_url_update_time

    # ------------ Speaker Level ----------------

    async def set_speaker_level(self, speaker: SpeakerIdentifier, level: int):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/channelVolume",
            property="x.com.samsung.networkaudio.channelVolume",
            value=[{"name": speaker.value, "value": level}],
        )

    async def set_rear_speaker_mode(self, mode: RearSpeakerMode):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/surroundspeaker",
            property="x.com.samsung.networkaudio.currentRearPosition",
            value=mode.value,
        )

    # ------------ OTHER FUNCTIONS ------------

    async def set_active_voice_amplifier(self, enabled: bool):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/activeVoiceAmplifier",
            property="x.com.samsung.networkaudio.activeVoiceAmplifier",
            value=1 if enabled else 0,
        )

    async def set_space_fit_sound(self, enabled: bool):
        await self.set_custom_execution_data(
            href="/sec/networkaudio/spacefitSound",
            property="x.com.samsung.networkaudio.spacefitSound",
            value=1 if enabled else 0,
        )

    # ------------ SUPPORT FUNCTIONS ------------

    async def update_execution_data(self, argument: list[str]):
        await self.__smartthings.execute_device_command(
            self._device_id,
            Capability.EXECUTE,
            Command.EXECUTE,
            argument=argument,
        )

    async def set_custom_execution_data(self, href: str, property: str, value):
        argument = [href, {property: value}]
        await self.__smartthings.execute_device_command(
            self._device_id,
            Capability.EXECUTE,
            Command.EXECUTE,
            argument=argument,
        )

    async def get_execute_status(self):
        payload: dict[str, Any] = {}
        get_method = getattr(self.__smartthings, "_get", None)
        if get_method is None:
            log.error(
                "[%s] Error: SmartThings client does not expose `_get` for execute status",
                DOMAIN,
            )
            return payload

        now = datetime.datetime.now()
        if self.__execute_retry_at and now < self.__execute_retry_at:
            await asyncio.sleep((self.__execute_retry_at - now).total_seconds())

        raw = await get_method(
            f"v1/devices/{self._device_id}/components/main/capabilities/execute/status"
        )
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return payload

            error = parsed.get("error")
            retry_delay = self._extract_too_many_requests_delay(error)
            if retry_delay is not None:
                self.__execute_retry_at = datetime.datetime.now() + datetime.timedelta(
                    seconds=retry_delay
                )
                log.warning(
                    "[%s] Execute status API rate-limited for %s. retrying in %.1fs",
                    DOMAIN,
                    self._device_id,
                    retry_delay,
                )
                return payload
            if isinstance(error, dict):
                log.warning(
                    "[%s] Execute status API error for %s: %s",
                    DOMAIN,
                    self._device_id,
                    error,
                )
                return payload

            self.__execute_retry_at = None

            data = parsed.get("data")
            if not isinstance(data, dict):
                return payload

            value = data.get("value")
            if not isinstance(value, dict):
                return payload

            response_payload = value.get("payload")
            if isinstance(response_payload, dict):
                payload = response_payload
        except json.JSONDecodeError:
            log.error("[%s] Error: Invalid execute status response for %s", DOMAIN, self._device_id)
        return payload

    async def get_song_title_artwork(self, artist: str, title: str) -> str:
        """
        This function loads a Music Art Cover from iTunes based on
        the title and the artist
        :param artist: string
        :param title: string
        :return: url as string
        """
        session = self.__session or getattr(self.__smartthings, "session", None)
        if session is None:
            return ""

        query_term = f"{artist} {title}"
        url = "https://itunes.apple.com/search?term=%s&media=music&entity=%s" % (
            quote(query_term),
            "musicTrack",
        )
        resp = await session.get(url)
        resp_dict = json.loads(await resp.text())
        if len(resp_dict["results"]) != 0:
            return resp_dict["results"][0]["artworkUrl100"]
        return ""

    @property
    def retrieve_data(self):
        woofer_level = self.woofer_level if self.__enable_woofer else None
        woofer_connection = self.woofer_connection if self.__enable_woofer else None
        sound_mode = self.sound_mode if self.__enable_soundmode else None
        supported_sound_modes = self.supported_soundmodes if self.__enable_soundmode else None
        night_mode = self.night_mode if self.__enable_advanced_audio else None
        bass_mode = self.bass_mode if self.__enable_advanced_audio else None
        voice_amplifier = self.voice_amplifier if self.__enable_advanced_audio else None
        active_eq_preset = self.active_equalizer_preset if self.__enable_eq else None
        supported_eq_presets = self.supported_equalizer_presets if self.__enable_eq else None
        equalizer_action = self.equalizer_action if self.__enable_eq else None
        equalizer_bands = self.equalizer_bands if self.__enable_eq else None
        playback_status = self._get_status_value(Capability.MEDIA_PLAYBACK, "playbackStatus")
        supported_playback_commands = self._get_status_value(
            Capability.MEDIA_PLAYBACK,
            "supportedPlaybackCommands",
            default=[],
        )
        available_capabilities = []
        main_status = self.__status_data.get("main")
        if isinstance(main_status, dict):
            available_capabilities = sorted(main_status.keys())

        status_retry_until = (
            self.__status_retry_at.isoformat() if self.__status_retry_at else None
        )
        execute_retry_until = (
            self.__execute_retry_at.isoformat() if self.__execute_retry_at else None
        )
        media_cover_updated = (
            self.media_coverart_updated.isoformat() if self.media_coverart_updated else None
        )

        return {
            "status": self.state,
            "device_information": {
                "model": self.model,
                "manufacture": self.manufacturer,
                "firmware_version": self.firmware_version,
                "device_id": self.device_id,
                "name": self.device.name,
                "label": self.device.label,
                "type": str(self.device.type),
                "location_id": self.device.location_id,
                "room_id": self.device.room_id,
            },
            "volume": {"level": self.volume_level, "muted": self.volume_muted},
            "woofer": {
                "level": woofer_level,
                "connection": woofer_connection,
            },
            "source": {
                "active_source": self.input_source,
                "supported_sources": self.supported_input_sources,
                "media_app_name": self.media_app_name,
            },
            "playback": {
                "status": playback_status,
                "supported_commands": supported_playback_commands,
            },
            "sound_mode": {
                "active_sound_mode": sound_mode,
                "supported_sound_modes": supported_sound_modes,
            },
            "advanced_audio": {
                "night_mode": night_mode,
                "bass_mode": bass_mode,
                "voice_amplifier": voice_amplifier,
            },
            "equalizer": {
                "active_preset": active_eq_preset,
                "supported_presets": supported_eq_presets,
                "action": equalizer_action,
                "bands": equalizer_bands,
            },
            "media": {
                "media_title": self.media_title,
                "media_artist": self.media_artist,
                "media_cover_url": self.media_coverart_url,
                "media_duration": self.media_duration,
                "media_position": self.media_position,
                "media_cover_updated": media_cover_updated,
            },
            "capabilities": {
                "available_main_capabilities": available_capabilities,
                "feature_flags": {
                    "enable_soundmode": self.__enable_soundmode,
                    "enable_advanced_audio": self.__enable_advanced_audio,
                    "enable_woofer": self.__enable_woofer,
                    "enable_eq": self.__enable_eq,
                },
            },
            "timestamps": {
                "switch": self._get_status_timestamp(Capability.SWITCH, "switch"),
                "volume": self._get_status_timestamp(Capability.AUDIO_VOLUME, "volume"),
                "mute": self._get_status_timestamp(Capability.AUDIO_MUTE, "mute"),
                "playback_status": self._get_status_timestamp(
                    Capability.MEDIA_PLAYBACK,
                    "playbackStatus",
                ),
                "audio_track": self._get_status_timestamp(
                    Capability.AUDIO_TRACK_DATA,
                    "audioTrackData",
                ),
                "media_position": self._get_status_timestamp(
                    Capability.AUDIO_TRACK_DATA,
                    "elapsedTime",
                ),
                "media_duration": self._get_status_timestamp(
                    Capability.AUDIO_TRACK_DATA,
                    "totalTime",
                ),
            },
            "api_backoff": {
                "status_retry_until": status_retry_until,
                "execute_retry_until": execute_retry_until,
            },
        }
