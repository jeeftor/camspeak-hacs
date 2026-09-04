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
        "describe",
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
            update_interval=timedelta(seconds=60),
            config_entry=entry,
        )
        self.client = client
        self._sse_task: asyncio.Task | None = None
        self._level_task: asyncio.Task | None = None
        self._prev_voices: list[str] = []
        # Real-time audio levels from /api/stream-levels SSE, keyed by camera name.
        # Updated by the level SSE listener between coordinator polls.
        self.live_levels: dict[str, float] = {}

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
            pb = playback.get(name, {})
            # Merge live SSE level if available (more recent than polled data)
            if name in self.live_levels:
                pb = {**pb, "level": self.live_levels[name]}
            camera_data[name] = CameraData(
                camera=merged,
                playback=pb,
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
        """Start listening to the SSE event and stream-levels streams."""
        self._sse_task = asyncio.create_task(self._sse_loop())
        self._level_task = asyncio.create_task(self._level_loop())

    async def async_stop_sse_listener(self) -> None:
        """Stop the SSE listeners."""
        for task in (self._sse_task, self._level_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._sse_task = None
        self._level_task = None
        self.live_levels.clear()

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

    async def _level_loop(self) -> None:
        """Listen to /api/stream-levels SSE for real-time audio levels.

        Updates self.live_levels without triggering a full coordinator refresh.
        The sensor entities read this via coordinator data on their next update.
        """
        url = f"{self.client._base_url}/api/stream-levels"  # noqa: SLF001
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
                            levels = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        self.live_levels = levels
                        # Notify entities so they pick up the new levels
                        self.async_update_listeners()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug("Level SSE connection lost: %s — reconnecting in 5s", exc)
                await asyncio.sleep(5)
