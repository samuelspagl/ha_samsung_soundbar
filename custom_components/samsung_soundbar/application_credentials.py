"""Application credentials for Samsung Soundbar."""

from homeassistant.components.application_credentials import AuthorizationServer


async def async_get_authorization_server(hass):
    """Return the SmartThings OAuth2 authorization server."""
    return AuthorizationServer(
        authorize_url="https://api.smartthings.com/oauth/authorize",
        token_url="https://api.smartthings.com/oauth/token",
    )
