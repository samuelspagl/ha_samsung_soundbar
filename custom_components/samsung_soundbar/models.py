from dataclasses import dataclass

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from pysmartthings import SmartThings

from .api_extension.SoundbarDevice import SoundbarDevice


@dataclass
class SoundbarRuntimeData:
    api: SmartThings
    device: SoundbarDevice
    oauth_session: OAuth2Session | None
