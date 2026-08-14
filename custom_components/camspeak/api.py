"""Async API client for the camspeak server."""

from typing import Any

from aiohttp import ClientResponse, ClientSession, ClientTimeout


class CamspeakApiClientError(Exception):
    """General API error."""


class CamspeakApiClient:
    """Thin async wrapper around the camspeak REST API."""

    def __init__(
        self,
        base_url: str,
        session: ClientSession,
    ) -> None:
        """Initialize the client."""
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request to the camspeak API."""
        url = f"{self._base_url}{endpoint}"
        try:
            async with (
                self._session.request(
                    method, url, json=json_data, timeout=ClientTimeout(total=30)
                ) as resp,
            ):
                if resp.status >= 400:  # noqa: PLR2004
                    text = await resp.text()
                    raise CamspeakApiClientError(
                        f"{method} {endpoint} returned {resp.status}: {text}"
                    )
                return await _parse_response(resp)
        except CamspeakApiClientError:
            raise
        except Exception as exc:
            raise CamspeakApiClientError(f"Connection error calling {endpoint}: {exc}") from exc

    async def health(self) -> dict[str, Any]:
        """GET /api/health."""
        return await self._request("GET", "/api/health")

    async def get_cameras(self) -> list[dict[str, Any]]:
        """GET /api/cameras — live status (online, ip, type)."""
        return await self._request("GET", "/api/cameras")

    async def get_config_cameras(self) -> list[dict[str, Any]]:
        """GET /api/config/cameras — config (gain, channel, stream, user)."""
        return await self._request("GET", "/api/config/cameras")

    async def get_playback(self) -> dict[str, Any]:
        """GET /api/playback."""
        return await self._request("GET", "/api/playback")

    async def get_library(self) -> list[dict[str, Any]]:
        """GET /api/library."""
        return await self._request("GET", "/api/library")

    async def get_voices(self) -> list[str]:
        """GET /api/voices — available TTS voices."""
        return await self._request("GET", "/api/voices")

    async def update_camera(self, camera: dict[str, Any]) -> dict[str, Any]:
        """POST /api/config/cameras — add or update a camera."""
        return await self._request("POST", "/api/config/cameras", json_data=camera)

    async def set_volume(self, camera: str, gain: float) -> dict[str, Any]:
        """PUT /api/cameras/:name/volume — set runtime gain (0-10).

        Takes effect immediately on the next audio chunk without restarting
        playback. Also persists to camera config.
        """
        return await self._request(
            "PUT", f"/api/cameras/{camera}/volume", json_data={"gain": gain}
        )

    async def play_preset(
        self,
        camera: str,
        preset: str,
        category: str = "",
        gain: float = 0,
        loop: bool = False,
    ) -> dict[str, Any]:
        """POST /api/play."""
        data: dict[str, Any] = {"camera": camera, "preset": preset}
        if category:
            data["category"] = category
        if gain > 0:
            data["gain"] = gain
        if loop:
            data["loop"] = True
        return await self._request("POST", "/api/play", json_data=data)

    async def speak(
        self,
        camera: str,
        text: str,
        voice: str = "",
        gain: float = 0,
    ) -> dict[str, Any]:
        """POST /api/speak."""
        data: dict[str, Any] = {"camera": camera, "text": text}
        if voice:
            data["voice"] = voice
        if gain > 0:
            data["gain"] = gain
        return await self._request("POST", "/api/speak", json_data=data)

    async def broadcast(
        self,
        text: str = "",
        preset: str = "",
        category: str = "",
        voice: str = "",
        gain: float = 0,
    ) -> dict[str, Any]:
        """POST /api/broadcast."""
        data: dict[str, Any] = {}
        if text:
            data["text"] = text
        if preset:
            data["preset"] = preset
        if category:
            data["category"] = category
        if voice:
            data["voice"] = voice
        if gain > 0:
            data["gain"] = gain
        return await self._request("POST", "/api/broadcast", json_data=data)

    async def play_stream(self, camera: str, url: str) -> dict[str, Any]:
        """POST /api/play-stream."""
        return await self._request(
            "POST", "/api/play-stream", json_data={"camera": camera, "url": url}
        )

    async def play_url(self, camera: str, url: str) -> dict[str, Any]:
        """POST /api/play-url."""
        return await self._request(
            "POST", "/api/play-url", json_data={"camera": camera, "url": url}
        )

    async def beep(self, camera: str) -> dict[str, Any]:
        """POST /api/beep."""
        return await self._request("POST", "/api/beep", json_data={"camera": camera})

    async def stop(self, camera: str = "") -> dict[str, Any]:
        """POST /api/stop."""
        data = {"camera": camera} if camera else {}
        return await self._request("POST", "/api/stop", json_data=data)

    async def pause(self, camera: str = "") -> dict[str, Any]:
        """POST /api/pause."""
        data = {"camera": camera} if camera else {}
        return await self._request("POST", "/api/pause", json_data=data)

    async def resume(self, camera: str = "") -> dict[str, Any]:
        """POST /api/resume."""
        data = {"camera": camera} if camera else {}
        return await self._request("POST", "/api/resume", json_data=data)


async def _parse_response(resp: ClientResponse) -> Any:
    """Parse response body as JSON or text."""
    if resp.content_type == "application/json":
        return await resp.json()
    return await resp.text()
