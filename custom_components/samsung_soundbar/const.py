from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

DOMAIN = "samsung_soundbar"
CONF_CLOUD_INTEGRATION = "cloud_integration"
CONF_ENTRY_API_KEY = "api_key"
CONF_ENTRY_DEVICE_ID = "device_id"
CONF_ENTRY_DEVICE_NAME = "device_name"
CONF_ENTRY_MAX_VOLUME = "device_volume"

CONF_ENTRY_SETTINGS_ADVANCED_AUDIO_SWITCHES = "settings_advanced_audio"
CONF_ENTRY_SETTINGS_EQ_SELECTOR = "settings_eq"
CONF_ENTRY_SETTINGS_SOUNDMODE_SELECTOR = "settings_soundmode"
CONF_ENTRY_SETTINGS_WOOFER_NUMBER = "settings_woofer"

DEFAULT_NAME = DOMAIN

BUTTON = BUTTON_DOMAIN
SWITCH = SWITCH_DOMAIN
MEDIA_PLAYER = MEDIA_PLAYER_DOMAIN
SELECT = SELECT_DOMAIN
SUPPORTED_DOMAINS = ["media_player", "switch"]


PLATFORMS = [SWITCH, MEDIA_PLAYER, SELECT, BUTTON]
