"""DataUpdateCoordinator for camspeak."""

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import dataclass
from datetime import timedelta
import json
from typing import override

from aiohttp import ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import CamspeakApiClient, CamspeakApiClientError
from .const import DOMAIN, LOGGER

type CamspeakConfigEntry = ConfigEntry["CamspeakCoordinator"]

# Actions that indicate playback state changed and warrant a refresh
_REFRESH_ACTIONS = frozenset(
    {
        "speak",
        "play",
        "play-stream",
        "play-url",
        "stop",
        "stop-all",
        "pause",
        "resume",
        "beep",
    }
)


@dataclass
class CameraData:
    """Per-camera data from camspeak."""

    camera: dict
    playback: dict
    presets: list[dict]
    preset_names: list[str]


@dataclass
class CamspeakData:
    """All data fetched from camspeak."""

    cameras: dict[str, CameraData]
    voices: list[str]
    preset_names: list[str]
    categories: list[str]


class CamspeakCoordinator(DataUpdateCoordinator[CamspeakData]):
    """Coordinator that polls camspeak and listens to SSE for real-time updates."""

    config_entry: CamspeakConfigEntry
    async_on_voice_change: Callable[[list[str]], None] | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CamspeakConfigEntry,
        client: CamspeakApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
            config_entry=entry,
        )
        self.client = client
        self._sse_task: asyncio.Task | None = None
        self._prev_voices: list[str] = []

    @override
    async def _async_update_data(self) -> CamspeakData:
        """Fetch cameras, playback state, and presets from camspeak."""
        try:
            cameras = await self.client.get_cameras()
            config_cameras = await self.client.get_config_cameras()
            playback = await self.client.get_playback()
            presets = await self.client.get_library()
            voices = await self.client.get_voices()
        except CamspeakApiClientError as exc:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(exc)},
            ) from exc

        # Merge live status (online, ip) with config (gain, channel, stream)
        config_by_name = {c["name"]: c for c in config_cameras}
        preset_names = [p["name"] for p in presets]
        categories = sorted({p.get("category", "") for p in presets if p.get("category")})
        camera_data: dict[str, CameraData] = {}
        for cam in cameras:
            name = cam["name"]
            merged = {**cam, **config_by_name.get(name, {})}
            camera_data[name] = CameraData(
                camera=merged,
                playback=playback.get(name, {}),
                presets=presets,
                preset_names=preset_names,
            )

        result = CamspeakData(
            cameras=camera_data,
            voices=voices,
            preset_names=preset_names,
            categories=categories,
        )

        if self.async_on_voice_change and voices != self._prev_voices:
            self._prev_voices = list(voices)
            self.async_on_voice_change(voices)

        return result

    async def async_start_sse_listener(self) -> None:
        """Start listening to the SSE event stream."""
        self._sse_task = asyncio.create_task(self._sse_loop())

    async def async_stop_sse_listener(self) -> None:
        """Stop the SSE listener."""
        if self._sse_task:
            self._sse_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sse_task
            self._sse_task = None

    async def _sse_loop(self) -> None:
        """Listen to SSE events and trigger refresh on playback changes."""
        url = f"{self.client._base_url}/api/events"  # noqa: SLF001
        while True:
            try:
                async with self.client._session.get(  # noqa: SLF001
                    url, timeout=ClientTimeout(total=None), raise_for_status=True
                ) as resp:
                    async for raw_line in resp.content:
                        line = raw_line.strip()
                        if not line or not line.startswith(b"data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        action = event.get("action", "")
                        if action in _REFRESH_ACTIONS:
                            LOGGER.debug(
                                "SSE event: %s on %s — refreshing",
                                action,
                                event.get("camera"),
                            )
                            await self.async_request_refresh()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug("SSE connection lost: %s — reconnecting in 5s", exc)
                await asyncio.sleep(5)
