"""Async API client for the camspeak server."""

from collections.abc import AsyncIterator
from contextlib import aclosing
from http import HTTPStatus
from typing import Any
from urllib.parse import quote, urlencode

from aiohttp import ClientResponse, ClientSession, ClientTimeout, FormData


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

    async def get_config(self) -> Any:
        """GET /api/config; no automatic retries."""
        return await self._request("GET", "/api/config")

    async def get_settings(self) -> Any:
        """GET /api/config/settings; no automatic retries."""
        return await self._request("GET", "/api/config/settings")

    async def update_settings(self, payload: dict[str, Any]) -> Any:
        """PUT /api/config/settings; no automatic retries."""
        return await self._request("PUT", "/api/config/settings", json_data=payload)

    async def test_settings(self, payload: dict[str, Any]) -> Any:
        """POST /api/config/settings/test; no automatic retries."""
        return await self._request("POST", "/api/config/settings/test", json_data=payload)

    async def get_vision_config(self) -> Any:
        """GET /api/config/vision; no automatic retries."""
        return await self._request("GET", "/api/config/vision")

    async def update_vision_config(self, payload: dict[str, Any]) -> Any:
        """PUT /api/config/vision; no automatic retries."""
        return await self._request("PUT", "/api/config/vision", json_data=payload)

    async def test_vision_config(self, payload: dict[str, Any]) -> Any:
        """POST /api/config/vision/test; no automatic retries."""
        return await self._request("POST", "/api/config/vision/test", json_data=payload)

    async def get_vision_prompts(self) -> Any:
        """GET /api/config/vision-prompts; no automatic retries."""
        return await self._request("GET", "/api/config/vision-prompts")

    async def save_vision_prompt(self, payload: dict[str, Any]) -> Any:
        """POST /api/config/vision-prompts; no automatic retries."""
        return await self._request("POST", "/api/config/vision-prompts", json_data=payload)

    async def delete_vision_prompt(self, name: str) -> Any:
        """DELETE /api/config/vision-prompts/{name}; no automatic retries."""
        return await self._request("DELETE", f"/api/config/vision-prompts/{quote(name, safe='')}")

    async def get_tts_presets(self) -> Any:
        """GET /api/config/tts; no automatic retries."""
        return await self._request("GET", "/api/config/tts")

    async def create_tts_preset(self, payload: dict[str, Any]) -> Any:
        """POST /api/config/tts; no automatic retries."""
        return await self._request("POST", "/api/config/tts", json_data=payload)

    async def update_tts_preset(self, name: str, payload: dict[str, Any]) -> Any:
        """PUT /api/config/tts/{name}; no automatic retries."""
        return await self._request(
            "PUT", f"/api/config/tts/{quote(name, safe='')}", json_data=payload
        )

    async def delete_tts_preset(self, name: str) -> Any:
        """DELETE /api/config/tts/{name}; no automatic retries."""
        return await self._request("DELETE", f"/api/config/tts/{quote(name, safe='')}")

    async def activate_tts_preset(self, name: str) -> Any:
        """POST /api/config/tts/{name}/activate; no automatic retries."""
        return await self._request("POST", f"/api/config/tts/{quote(name, safe='')}/activate")

    async def reorder_cameras(self, payload: dict[str, Any]) -> Any:
        """POST /api/config/cameras/reorder; no automatic retries."""
        return await self._request("POST", "/api/config/cameras/reorder", json_data=payload)

    async def detect_camera(self, payload: dict[str, Any]) -> Any:
        """POST /api/config/cameras/detect; no automatic retries."""
        return await self._request("POST", "/api/config/cameras/detect", json_data=payload)

    async def discover_cameras(self) -> Any:
        """POST /api/config/cameras/discover; no automatic retries."""
        return await self._request("POST", "/api/config/cameras/discover")

    async def toggle_camera(self, name: str) -> Any:
        """PATCH /api/config/cameras/{name}/toggle; no automatic retries."""
        return await self._request("PATCH", f"/api/config/cameras/{quote(name, safe='')}/toggle")

    async def delete_camera(self, name: str) -> Any:
        """DELETE /api/config/cameras/{name}; no automatic retries."""
        return await self._request("DELETE", f"/api/config/cameras/{quote(name, safe='')}")

    async def get_go2rtc_streams(self) -> Any:
        """GET /api/config/go2rtc/streams; no automatic retries."""
        return await self._request("GET", "/api/config/go2rtc/streams")

    async def get_airplay_config(self) -> Any:
        """GET /api/config/airplay; no automatic retries."""
        return await self._request("GET", "/api/config/airplay")

    async def update_airplay_config(self, payload: dict[str, Any]) -> Any:
        """PUT /api/config/airplay; no automatic retries."""
        return await self._request("PUT", "/api/config/airplay", json_data=payload)

    async def toggle_camera_airplay(self, camera: str) -> Any:
        """PATCH /api/config/airplay/{camera}/toggle; no automatic retries."""
        return await self._request("PATCH", f"/api/config/airplay/{quote(camera, safe='')}/toggle")

    async def ping_camera(self, camera: str) -> Any:
        """POST /api/cameras/{camera}/ping; no automatic retries."""
        return await self._request("POST", f"/api/cameras/{quote(camera, safe='')}/ping")

    async def get_camera_info(self, camera: str) -> Any:
        """GET /api/cameras/{camera}/info; no automatic retries."""
        return await self._request("GET", f"/api/cameras/{quote(camera, safe='')}/info")

    async def get_streams(self) -> Any:
        """GET /api/streams; no automatic retries."""
        return await self._request("GET", "/api/streams")

    async def vision(self, payload: dict[str, Any]) -> Any:
        """POST /api/vision; no automatic retries."""
        return await self._request("POST", "/api/vision", json_data=payload)

    async def test_vision(self, payload: dict[str, Any]) -> Any:
        """POST /api/vision/test; no automatic retries."""
        return await self._request("POST", "/api/vision/test", json_data=payload)

    async def test_all_vision_models(self, payload: dict[str, Any]) -> Any:
        """POST /api/vision/test-all; no automatic retries."""
        return await self._request("POST", "/api/vision/test-all", json_data=payload)

    async def describe(self, payload: dict[str, Any]) -> Any:
        """POST /api/describe; no automatic retries."""
        return await self._request("POST", "/api/describe", json_data=payload)

    async def generate_preset(self, payload: dict[str, Any]) -> Any:
        """POST /api/library; no automatic retries."""
        return await self._request("POST", "/api/library", json_data=payload)

    async def get_upload_job(self, name: str) -> Any:
        """GET /api/library/upload/jobs/{name}; no automatic retries."""
        return await self._request("GET", f"/api/library/upload/jobs/{quote(name, safe='')}")

    async def delete_preset(self, category: str, name: str) -> Any:
        """DELETE /api/library/{category}/{name}; no automatic retries."""
        return await self._request(
            "DELETE", f"/api/library/{quote(category, safe='')}/{quote(name, safe='')}"
        )

    async def rename_preset(self, category: str, name: str, payload: dict[str, Any]) -> Any:
        """PATCH /api/library/{category}/{name}; no automatic retries."""
        return await self._request(
            "PATCH",
            f"/api/library/{quote(category, safe='')}/{quote(name, safe='')}",
            json_data=payload,
        )

    async def get_preset_peaks(self, category: str, name: str) -> Any:
        """GET /api/library/{category}/{name}/peaks; no automatic retries."""
        return await self._request(
            "GET", f"/api/library/{quote(category, safe='')}/{quote(name, safe='')}/peaks"
        )

    async def analyze_preset(self, category: str, name: str) -> Any:
        """GET /api/library/{category}/{name}/analyze; no automatic retries."""
        return await self._request(
            "GET", f"/api/library/{quote(category, safe='')}/{quote(name, safe='')}/analyze"
        )

    async def set_preset_gain(self, category: str, name: str, payload: dict[str, Any]) -> Any:
        """PUT /api/library/{category}/{name}/gain; no automatic retries."""
        return await self._request(
            "PUT",
            f"/api/library/{quote(category, safe='')}/{quote(name, safe='')}/gain",
            json_data=payload,
        )

    async def get_openapi(self) -> Any:
        """GET /api/openapi.json; no automatic retries."""
        return await self._request("GET", "/api/openapi.json")

    async def snapshot(self, camera: str, **options: str | int) -> bytes:
        """Fetch an image; options are method, stream and width."""
        path = f"/api/snapshot/{quote(camera, safe='')}"
        if options:
            path += "?" + urlencode(options)
        return await self._request("GET", path)

    async def benchmark_snapshot(
        self, camera: str, *, vision: bool = False, prompt: str = ""
    ) -> Any:
        """Compare capture methods without speaker playback."""
        query = urlencode({"vision": str(vision).lower(), "prompt": prompt})
        return await self._request(
            "GET", f"/api/snapshot/{quote(camera, safe='')}/benchmark?{query}"
        )

    async def preview_preset(self, category: str, name: str) -> bytes:
        """Download preview audio without camera playback."""
        return await self._request(
            "GET", f"/api/library/{quote(category, safe='')}/{quote(name, safe='')}/preview"
        )

    async def upload_preset(
        self, name: str, filename: str, audio: bytes, category: str = "uploads"
    ) -> Any:
        """Upload audio once; poll get_upload_job before using the new preset."""
        form = FormData()
        form.add_field("file", audio, filename=filename, content_type="application/octet-stream")
        form.add_field("category", category)
        form.add_field("name", name)
        async with self._session.post(
            self._base_url + "/api/library/upload", data=form, timeout=ClientTimeout(total=120)
        ) as resp:
            if resp.status >= HTTPStatus.BAD_REQUEST:
                raise CamspeakApiClientError(f"Upload returned HTTP {resp.status}")
            return await _parse_response(resp)

    async def stream_events(self) -> AsyncIterator[bytes]:
        """Yield raw SSE chunks; closing the iterator closes the subscription."""
        async with aclosing(self._stream("GET", "/api/events")) as stream:
            async for chunk in stream:
                yield chunk

    async def stream_levels(self) -> AsyncIterator[bytes]:
        """Yield raw level-event SSE chunks, not JSON responses."""
        async with aclosing(self._stream("GET", "/api/stream-levels")) as stream:
            async for chunk in stream:
                yield chunk

    async def stream_benchmark(self, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        """Stream the benchmark matrix once; do not retry interrupted starts."""
        async with aclosing(self._stream("POST", "/api/benchmark", payload)) as stream:
            async for chunk in stream:
                yield chunk

    async def stream_vision_comparison(self, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        """Stream model comparisons once without camera playback."""
        async with aclosing(self._stream("POST", "/api/vision/test-all/stream", payload)) as stream:
            async for chunk in stream:
                yield chunk

    async def _stream(
        self, method: str, endpoint: str, payload: dict[str, Any] | None = None
    ) -> AsyncIterator[bytes]:
        """Keep response lifetime scoped to consumption; never replay a request."""
        async with self._session.request(
            method,
            self._base_url + endpoint,
            json=payload,
            timeout=ClientTimeout(total=None, sock_connect=30),
        ) as resp:
            if resp.status >= HTTPStatus.BAD_REQUEST or resp.content_type != "text/event-stream":
                raise CamspeakApiClientError(
                    f"Expected SSE from {endpoint}; HTTP {resp.status}, type {resp.content_type}"
                )
            async for chunk in resp.content.iter_any():
                yield chunk

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

    async def test_tts_model(self, url: str, model: str = "", api_key: str = "") -> dict[str, Any]:
        """Check the endpoint catalog and an optional exact model ID without playback."""
        return await self._request(
            "POST", "/api/config/tts/test", {"url": url, "model": model, "api_key": api_key}
        )

    async def set_camera_tts_mode(self, camera: dict[str, Any], mode: str = "") -> dict[str, Any]:
        """Override camera speech mode, or inherit the preset with an empty mode."""
        if mode not in ("", "buffered", "streaming"):
            raise ValueError("Mode must be empty, buffered or streaming")
        return await self._request("POST", "/api/config/cameras", {**camera, "tts_mode": mode})

    async def get_library(self) -> list[dict[str, Any]]:
        """GET /api/library."""
        return await self._request("GET", "/api/library")

    async def start_speaker_benchmark(
        self,
        camera: str,
        preset: str,
        text: str,
        *,
        confirm_playback: bool,
        voice: str = "",
        sample_rate: int = 24000,
        channels: int = 1,
        streaming_first: bool = False,
    ) -> dict[str, Any]:
        """Start explicitly confirmed camera playback; poll the returned job identifier."""
        return await self._request(
            "POST",
            "/api/config/tts/benchmark/speaker",
            {
                "camera": camera,
                "preset": preset,
                "text": text,
                "voice": voice,
                "confirm_playback": confirm_playback,
                "sample_rate": sample_rate,
                "channels": channels,
                "streaming_first": streaming_first,
            },
        )

    async def get_speaker_benchmark(self, job_id: str) -> dict[str, Any]:
        """Read retained comparison results without replaying audio."""
        return await self._request(
            "GET", f"/api/config/tts/benchmark/jobs/{quote(job_id, safe='')}"
        )

    async def cancel_speaker_benchmark(self, job_id: str) -> dict[str, Any]:
        """Cancel only the selected comparison job."""
        return await self._request(
            "DELETE", f"/api/config/tts/benchmark/jobs/{quote(job_id, safe='')}"
        )

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
        return await self._request("GET", f"/api/describe/jobs/{quote(job_id, safe='')}")

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
    """Preserve binary audio/images; parse JSON and textual responses normally."""
    if (
        resp.content_type.startswith(("audio/", "image/"))
        or resp.content_type == "application/octet-stream"
    ):
        return await resp.read()
    if resp.content_type == "application/json":
        return await resp.json()
    return await resp.text()
