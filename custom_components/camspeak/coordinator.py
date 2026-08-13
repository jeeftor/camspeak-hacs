"""DataUpdateCoordinator for camspeak."""

from dataclasses import dataclass
from datetime import timedelta
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import CamspeakApiClient, CamspeakApiClientError
from .const import DOMAIN, LOGGER

type CamspeakConfigEntry = ConfigEntry["CamspeakCoordinator"]


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


class CamspeakCoordinator(DataUpdateCoordinator[CamspeakData]):
    """Coordinator that polls camspeak for cameras and playback state."""

    config_entry: CamspeakConfigEntry

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
            update_interval=timedelta(seconds=10),
            config_entry=entry,
        )
        self.client = client

    @override
    async def _async_update_data(self) -> CamspeakData:
        """Fetch cameras, playback state, and presets from camspeak."""
        try:
            cameras = await self.client.get_cameras()
            playback = await self.client.get_playback()
            presets = await self.client.get_library()
        except CamspeakApiClientError as exc:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(exc)},
            ) from exc

        preset_names = [p["name"] for p in presets]
        camera_data: dict[str, CameraData] = {}
        for cam in cameras:
            name = cam["name"]
            camera_data[name] = CameraData(
                camera=cam,
                playback=playback.get(name, {}),
                presets=presets,
                preset_names=preset_names,
            )

        return CamspeakData(cameras=camera_data)
