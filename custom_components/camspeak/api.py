"""Async API client for the camspeak server."""

from typing import Any
from urllib.parse import urlencode

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

    async def get_events(self, limit: int = 100, camera: str = "") -> list[dict[str, Any]]:
        """Get playback history, preserving optional replay metadata from newer servers."""
        query: dict[str, str | int] = {"limit": limit}
        if camera:
            query["camera"] = camera
        return await self._request("GET", f"/api/events/log?{urlencode(query)}")

    async def benchmark_tts(
        self,
        preset: str,
        mode: str,
        text: str,
        *,
        voice: str = "",
        sample_rate: int = 24000,
        channels: int = 1,
    ) -> dict[str, Any]:
        """Test a saved TTS preset without activating it or playing on cameras."""
        return await self._request(
            "POST",
            "/api/config/tts/benchmark",
            {
                "preset": preset,
                "mode": mode,
                "text": text,
                "voice": voice,
                "sample_rate": sample_rate,
                "channels": channels,
            },
        )

    async def get_library(self) -> list[dict[str, Any]]:
        """GET /api/library."""
        return await self._request("GET", "/api/library")

    async def get_voices(self) -> list[str]:
        """GET /api/voices — available TTS voices."""
        return await self._request("GET", "/api/voices")

    async def tts_preview(self, text: str, voice: str = "") -> bytes:
        """POST /api/tts/preview — generate TTS and return WAV bytes."""
        url = f"{self._base_url}/api/tts/preview"
        payload: dict[str, Any] = {"text": text}
        if voice:
            payload["voice"] = voice
        try:
            async with (
                self._session.post(url, json=payload, timeout=ClientTimeout(total=60)) as resp,
            ):
                if resp.status >= 400:  # noqa: PLR2004
                    text_resp = await resp.text()
                    raise CamspeakApiClientError(
                        f"POST /api/tts/preview returned {resp.status}: {text_resp}"
                    )
                return await resp.read()
        except CamspeakApiClientError:
            raise
        except Exception as exc:
            raise CamspeakApiClientError(
                f"Connection error calling /api/tts/preview: {exc}"
            ) from exc

    async def update_camera(self, camera: dict[str, Any]) -> dict[str, Any]:
        """POST /api/config/cameras — add or update a camera."""
        return await self._request("POST", "/api/config/cameras", json_data=camera)

    async def update_camera_capture(
        self, camera: dict[str, Any], method: str, stream: str = ""
    ) -> dict[str, Any]:
        """Save method/source together using your complete existing camera configuration.

        Direct API uses main/sub; go2rtc uses a named stream. Only auto falls back.
        """
        return await self.update_camera({**camera, "snap_method": method, "vision_stream": stream})

    async def set_volume(self, camera: str, gain: float) -> dict[str, Any]:
        """PUT /api/cameras/:name/volume — set runtime gain (0-10).

        Takes effect immediately on the next audio chunk without restarting
        playback. Also persists to camera config.
        """
        return await self._request("PUT", f"/api/cameras/{camera}/volume", json_data={"gain": gain})

    async def play_preset(
        self,
        camera: str,
        preset: str,
        category: str = "",
        gain: float | None = None,
        loop: int = 0,
    ) -> dict[str, Any]:
        """POST /api/play."""
        data: dict[str, Any] = {"camera": camera, "preset": preset}
        if category:
            data["category"] = category
        if gain is not None:
            data["gain"] = gain
        if loop != 0:
            data["loop"] = loop
        return await self._request("POST", "/api/play", json_data=data)

    async def speak(
        self,
        camera: str,
        text: str,
        voice: str = "",
        gain: float | None = None,
    ) -> dict[str, Any]:
        """POST /api/speak."""
        data: dict[str, Any] = {"camera": camera, "text": text}
        if voice:
            data["voice"] = voice
        if gain is not None:
            data["gain"] = gain
        return await self._request("POST", "/api/speak", json_data=data)

    async def announce(
        self,
        source_camera: str,
        target_camera: str,
        prompt: str = "",
        voice: str = "",
        gain: float | None = None,
    ) -> dict[str, Any]:
        """POST /api/announce — capture from source, vision, TTS, play on target."""
        data: dict[str, Any] = {
            "source_camera": source_camera,
            "target_camera": target_camera,
        }
        if prompt:
            data["prompt"] = prompt
        if voice:
            data["voice"] = voice
        if gain is not None:
            data["gain"] = gain
        return await self._request("POST", "/api/announce", json_data=data)

    async def start_describe_job(
        self,
        camera: str,
        prompt: str = "",
        stream: str = "",
        gain: float | None = None,
    ) -> dict[str, Any]:
        """Start a background Describe job without waiting through playback.

        Requires camspeak 4.2.1 or newer. Poll get_describe_job for progress;
        use stop to cancel your camera's operation. Do not automatically retry
        this start request if its response is lost: playback may have started.
        """
        data: dict[str, Any] = {"camera": camera}
        if prompt:
            data["prompt"] = prompt
        if stream:
            data["stream"] = stream
        if gain is not None:
            data["gain"] = gain
        return await self._request("POST", "/api/describe/jobs", json_data=data)

    async def get_describe_job(self, job_id: str) -> dict[str, Any]:
        """Read Describe progress, partial results, and completed stage timings.

        Poll until status is done, error, or canceled. Results expire after
        ten minutes or earlier eviction; a missing job does not prove that
        playback failed.
        """
        return await self._request("GET", f"/api/describe/jobs/{job_id}")

    async def broadcast(
        self,
        *,
        text: str = "",
        preset: str = "",
        category: str = "",
        voice: str = "",
        gain: float | None = None,
        loop: int = 0,
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
        if gain is not None:
            data["gain"] = gain
        if loop != 0:
            data["loop"] = loop
        return await self._request("POST", "/api/broadcast", json_data=data)

    async def play_stream(self, camera: str, url: str, gain: float | None = None) -> dict[str, Any]:
        """POST /api/play-stream."""
        data: dict[str, Any] = {"camera": camera, "url": url}
        if gain is not None:
            data["gain"] = gain
        return await self._request("POST", "/api/play-stream", json_data=data)

    async def play_url(self, camera: str, url: str, gain: float | None = None) -> dict[str, Any]:
        """POST /api/play-url."""
        data: dict[str, Any] = {"camera": camera, "url": url}
        if gain is not None:
            data["gain"] = gain
        return await self._request("POST", "/api/play-url", json_data=data)

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
