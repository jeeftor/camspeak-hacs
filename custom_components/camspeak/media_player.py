"""Media player platform for camspeak cameras."""

from typing import Any, override

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PLAYBACK_IDLE, PLAYBACK_PAUSED, PLAYBACK_PLAYING
from .coordinator import CamspeakCoordinator
from .entity import CamspeakEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[CamspeakCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up camspeak media players from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(CamspeakMediaPlayer(coordinator, name) for name in coordinator.data.cameras)


class CamspeakMediaPlayer(CamspeakEntity, MediaPlayerEntity):
    """Representation of a camspeak camera as a media player."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the media player."""
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{camera_name}_media_player"
        self._attr_name = "speaker"

    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self) -> None:
        """Update entity state from coordinator data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            self._attr_available = False
            return

        cam_data = data.cameras[self._camera_name]
        cam = cam_data.camera
        playback = cam_data.playback

        if not cam.get("online", False):
            self._attr_available = False
            return

        self._attr_available = True
        state = playback.get("state", PLAYBACK_IDLE)
        if state == PLAYBACK_PLAYING:
            self._attr_state = MediaPlayerState.PLAYING
        elif state == PLAYBACK_PAUSED:
            self._attr_state = MediaPlayerState.PAUSED
        else:
            self._attr_state = MediaPlayerState.IDLE

        detail = playback.get("detail", "")
        if detail:
            self._attr_media_title = detail

        self._attr_source_list = cam_data.preset_names

        gain = cam.get("gain", 3.0)
        if gain and gain > 0:
            self._attr_volume_level = min(gain / 10.0, 1.0)

    @override
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._update_state()

    @override
    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play media on the camera.

        media_type determines how camspeak handles it:
        - "music" or "preset": play a saved preset by name
        - "url": download audio file, transcode, play
        - "stream": stream live audio from URL/playlist
        """
        if media_type in ("url",):
            await self.coordinator.client.play_url(camera=self._camera_name, url=media_id)
        elif media_type in ("stream",):
            await self.coordinator.client.play_stream(camera=self._camera_name, url=media_id)
        else:
            await self.coordinator.client.play_preset(camera=self._camera_name, preset=media_id)
        await self.coordinator.async_request_refresh()

    @override
    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self.coordinator.client.pause(camera=self._camera_name)
        await self.coordinator.async_request_refresh()

    @override
    async def async_media_play(self) -> None:
        """Resume playback if paused."""
        if self.state == MediaPlayerState.PAUSED:
            await self.coordinator.client.resume(camera=self._camera_name)
            await self.coordinator.async_request_refresh()

    @override
    async def async_media_stop(self) -> None:
        """Stop playback."""
        await self.coordinator.client.stop(camera=self._camera_name)
        await self.coordinator.async_request_refresh()

    @override
    async def async_select_source(self, source: str) -> None:
        """Select a preset source."""
        await self.coordinator.client.play_preset(camera=self._camera_name, preset=source)
        self._attr_source = source
        await self.coordinator.async_request_refresh()

    @override
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (maps to camera gain 0-10)."""
        gain = round(volume * 10, 1)
        cam_data = self.coordinator.data.cameras.get(self._camera_name)
        if cam_data:
            cam = cam_data.camera
            await self.coordinator.client.update_camera(
                {
                    "name": self._camera_name,
                    "ip": cam.get("ip", ""),
                    "type": cam.get("type", "hikvision"),
                    "gain": gain,
                }
            )
        self._attr_volume_level = volume
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
