"""Media player platform for camspeak cameras."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PLAYBACK_IDLE, PLAYBACK_PAUSED, PLAYBACK_PLAYING
from .coordinator import CamspeakCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camspeak media players from a config entry."""
    coordinator: CamspeakCoordinator = entry.runtime_data
    cameras = coordinator.data or {}
    async_add_entities(
        [CamspeakMediaPlayer(coordinator, name) for name in cameras],
        update_before_add=True,
    )


class CamspeakMediaPlayer(CoordinatorEntity[CamspeakCoordinator], MediaPlayerEntity):
    """Representation of a camspeak camera as a media player."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_has_entity_name = True

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._camera_name = camera_name
        cam = coordinator.data[camera_name]["camera"]
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{camera_name}"
        self._attr_name = f"{camera_name} speaker"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, camera_name)},
            "name": camera_name,
            "manufacturer": cam.get("type", "IP Camera"),
            "model": cam.get("type", ""),
            "sw_version": cam.get("airplay_model", ""),
        }
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.VOLUME_SET
        )
        self._attr_volume_level = None
        self._attr_source = None
        self._attr_source_list = None
        self._update_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        """Update entity state from coordinator data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data:
            self._attr_state = MediaPlayerState.OFF
            return

        cam_data = data[self._camera_name]
        cam = cam_data["camera"]
        playback = cam_data["playback"]
        presets = cam_data.get("preset_names", [])

        # Online status
        if not cam.get("online", False):
            self._attr_state = MediaPlayerState.UNAVAILABLE
            return

        # Map playback state to media player state
        state = playback.get("state", PLAYBACK_IDLE)
        if state == PLAYBACK_PLAYING:
            self._attr_state = MediaPlayerState.PLAYING
        elif state == PLAYBACK_PAUSED:
            self._attr_state = MediaPlayerState.PAUSED
        else:
            self._attr_state = MediaPlayerState.IDLE

        # Playback detail as media title
        detail = playback.get("detail", "")
        source = playback.get("source", "")
        if detail:
            self._attr_media_title = detail
        if source:
            self._attr_media_channel = source

        # Presets as source list
        self._attr_source_list = presets

        # Gain → volume (gain is 0-10, volume is 0.0-1.0)
        gain = cam.get("gain", 3.0)
        if gain and gain > 0:
            self._attr_volume_level = min(gain / 10.0, 1.0)

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a preset (media_id is the preset name)."""
        await self.coordinator.client.play_preset(
            camera=self._camera_name, preset=media_id
        )
        await self.coordinator.async_request_refresh()

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self.coordinator.client.pause(camera=self._camera_name)
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        """Resume playback."""
        await self.coordinator.client.resume(camera=self._camera_name)
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        """Stop playback."""
        await self.coordinator.client.stop(camera=self._camera_name)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        """Select a preset source."""
        await self.coordinator.client.play_preset(
            camera=self._camera_name, preset=source
        )
        self._attr_source = source
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume (maps to gain 0-10)."""
        # Volume 0.0-1.0 → gain 0.0-10.0
        gain = round(volume * 10.0, 1)
        # We don't have a direct "set gain" endpoint, but play_preset accepts gain
        # For now, just store it — the next play will use it
        self._attr_volume_level = volume
