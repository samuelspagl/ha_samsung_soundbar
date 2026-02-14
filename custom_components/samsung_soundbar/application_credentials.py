"""Application credentials platform for Samsung Soundbar."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

SMARTTHINGS_AUTHORIZE_URL = "https://api.smartthings.com/oauth/authorize"
SMARTTHINGS_TOKEN_URL = "https://api.smartthings.com/oauth/token"


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the SmartThings OAuth2 authorization server."""
    return AuthorizationServer(
        authorize_url=SMARTTHINGS_AUTHORIZE_URL,
        token_url=SMARTTHINGS_TOKEN_URL,
    )
