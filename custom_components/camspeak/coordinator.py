"""Data update coordinator for camspeak."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CamspeakApiClient, CamspeakApiClientError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)


class CamspeakCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls camspeak for cameras and playback state."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: CamspeakApiClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch cameras, playback state, and presets from camspeak."""
        try:
            cameras = await self.client.get_cameras()
            playback = await self.client.get_playback()
            presets = await self.client.get_library()
        except CamspeakApiClientError as err:
            raise UpdateFailed(f"Error communicating with camspeak: {err}") from err

        # Build a lookup of preset names (for media player sources)
        preset_names = [p["name"] for p in presets]

        # Build per-camera data
        camera_data: dict[str, Any] = {}
        for cam in cameras:
            name = cam["name"]
            cam_playback = playback.get(name, {})
            camera_data[name] = {
                "camera": cam,
                "playback": cam_playback,
                "presets": presets,
                "preset_names": preset_names,
            }

        return camera_data
