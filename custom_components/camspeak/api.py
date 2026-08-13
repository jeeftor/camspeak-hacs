"""Async API client for the camspeak server."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    API_BROADCAST,
    API_BEEP,
    API_CAMERAS,
    API_HEALTH,
    API_LIBRARY,
    API_PAUSE,
    API_PLAY,
    API_PLAYBACK,
    API_PLAY_STREAM,
    API_PLAY_URL,
    API_RESUME,
    API_SPEAK,
    API_STOP,
    API_VOICES,
)

_LOGGER = logging.getLogger(__name__)


class CamspeakApiClientError(Exception):
    """General API error."""


class CamspeakApiClient:
    """Thin async wrapper around the camspeak REST API."""

    def __init__(
        self,
        base_url: str,
        verify_ssl: bool = True,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the client."""
        self._base_url = base_url.rstrip("/")
        self._verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = session
        self._own_session = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
            self._own_session = True
        return self._session

    async def close(self) -> None:
        """Close the underlying session if we own it."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> Any:
        """Make an HTTP request to the camspeak API."""
        url = f"{self._base_url}{endpoint}"
        session = await self._get_session()
        try:
            async with async_timeout.timeout(timeout):
                async with session.request(method, url, json=json_data) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise CamspeakApiClientError(
                            f"{method} {endpoint} returned {resp.status}: {text}"
                        )
                    if resp.content_type == "application/json":
                        return await resp.json()
                    return await resp.text()
        except asyncio.TimeoutError as err:
            raise CamspeakApiClientError(f"Timeout calling {endpoint}") from err
        except aiohttp.ClientError as err:
            raise CamspeakApiClientError(f"Connection error calling {endpoint}: {err}") from err

    # --- System endpoints ---

    async def health(self) -> dict[str, Any]:
        """GET /api/health."""
        return await self._request("GET", API_HEALTH)

    async def get_cameras(self) -> list[dict[str, Any]]:
        """GET /api/cameras — list all cameras with online status."""
        return await self._request("GET", API_CAMERAS)

    async def get_playback(self) -> dict[str, Any]:
        """GET /api/playback — playback state for all cameras."""
        return await self._request("GET", API_PLAYBACK)

    async def get_library(self) -> list[dict[str, Any]]:
        """GET /api/library — list all presets."""
        return await self._request("GET", API_LIBRARY)

    async def get_voices(self) -> list[str]:
        """GET /api/voices — list available TTS voices."""
        return await self._request("GET", API_VOICES)

    # --- Audio endpoints ---

    async def play_preset(
        self, camera: str, preset: str, category: str = "", gain: float = 0, loop: bool = False
    ) -> dict[str, Any]:
        """POST /api/play."""
        data: dict[str, Any] = {"camera": camera, "preset": preset}
        if category:
            data["category"] = category
        if gain > 0:
            data["gain"] = gain
        if loop:
            data["loop"] = True
        return await self._request("POST", API_PLAY, json_data=data)

    async def speak(
        self, camera: str, text: str, voice: str = "", gain: float = 0
    ) -> dict[str, Any]:
        """POST /api/speak."""
        data: dict[str, Any] = {"camera": camera, "text": text}
        if voice:
            data["voice"] = voice
        if gain > 0:
            data["gain"] = gain
        return await self._request("POST", API_SPEAK, json_data=data)

    async def broadcast(
        self, text: str = "", preset: str = "", voice: str = "", gain: float = 0
    ) -> dict[str, Any]:
        """POST /api/broadcast."""
        data: dict[str, Any] = {}
        if text:
            data["text"] = text
        if preset:
            data["preset"] = preset
        if voice:
            data["voice"] = voice
        if gain > 0:
            data["gain"] = gain
        return await self._request("POST", API_BROADCAST, json_data=data)

    async def play_stream(self, camera: str, url: str) -> dict[str, Any]:
        """POST /api/play-stream."""
        return await self._request(
            "POST", API_PLAY_STREAM, json_data={"camera": camera, "url": url}
        )

    async def play_url(self, camera: str, url: str) -> dict[str, Any]:
        """POST /api/play-url."""
        return await self._request(
            "POST", API_PLAY_URL, json_data={"camera": camera, "url": url}
        )

    async def beep(self, camera: str) -> dict[str, Any]:
        """POST /api/beep."""
        return await self._request("POST", API_BEEP, json_data={"camera": camera})

    async def stop(self, camera: str = "") -> dict[str, Any]:
        """POST /api/stop."""
        data = {"camera": camera} if camera else {}
        return await self._request("POST", API_STOP, json_data=data)

    async def pause(self, camera: str = "") -> dict[str, Any]:
        """POST /api/pause."""
        data = {"camera": camera} if camera else {}
        return await self._request("POST", API_PAUSE, json_data=data)

    async def resume(self, camera: str = "") -> dict[str, Any]:
        """POST /api/resume."""
        data = {"camera": camera} if camera else {}
        return await self._request("POST", API_RESUME, json_data=data)
