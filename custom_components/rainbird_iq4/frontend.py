"""Frontend support for Rain Bird IQ4."""

from __future__ import annotations

from pathlib import Path
import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

try:
    from homeassistant.components.http import StaticPathConfig
except ImportError:
    StaticPathConfig = None

from .const import (
    CARD_FILENAME,
    DATA_FRONTEND_REGISTERED,
    DATA_TOKEN_SESSIONS,
    DOMAIN,
    FRONTEND_URL_PATH,
    TOKEN_HELPER_FILENAME,
)
from .iq4_client import extract_access_token


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register static files and helper views for the bundled frontend."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_FRONTEND_REGISTERED):
        return

    www_path = Path(__file__).parent / "www"
    if StaticPathConfig is None or not hasattr(hass.http, "async_register_static_paths"):
        hass.http.register_static_path(
            f"{FRONTEND_URL_PATH}/{CARD_FILENAME}",
            str(www_path / CARD_FILENAME),
            True,
        )
        hass.http.register_static_path(
            f"{FRONTEND_URL_PATH}/{TOKEN_HELPER_FILENAME}",
            str(www_path / TOKEN_HELPER_FILENAME),
            True,
        )
    else:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"{FRONTEND_URL_PATH}/{CARD_FILENAME}",
                    str(www_path / CARD_FILENAME),
                    True,
                ),
                StaticPathConfig(
                    f"{FRONTEND_URL_PATH}/{TOKEN_HELPER_FILENAME}",
                    str(www_path / TOKEN_HELPER_FILENAME),
                    True,
                )
            ]
        )
    hass.http.register_view(RainBirdIQ4TokenCaptureView)

    domain_data[DATA_FRONTEND_REGISTERED] = True


class RainBirdIQ4TokenCaptureView(HomeAssistantView):
    """Receive a browser-captured IQ4 token for an active config flow."""

    url = "/api/rainbird_iq4/token_capture"
    name = "api:rainbird_iq4:token_capture"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except ValueError:
            return web.json_response({"error": "invalid_json"}, status=400)

        session_id = data.get("session")
        token = extract_access_token(data.get("token"))
        sessions = hass.data.setdefault(DOMAIN, {}).setdefault(DATA_TOKEN_SESSIONS, {})
        if not isinstance(session_id, str) or session_id not in sessions:
            return web.json_response({"error": "unknown_session"}, status=404)
        if not token:
            return web.json_response({"error": "invalid_token"}, status=400)

        sessions[session_id] = {
            "token": token,
            "updated_at": time.time(),
        }
        return web.json_response({"ok": True})
