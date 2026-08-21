"""Media player platform for camspeak cameras."""

import re
from typing import Any, override

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, PLAYBACK_IDLE, PLAYBACK_PAUSED, PLAYBACK_PLAYING
from .coordinator import CamspeakCoordinator
from .entity import CamspeakEntity

_CAMSPEAK_PRESET_PREFIX = "camspeak://preset/"
_CAMSPEAK_LIBRARY_PREFIX = "camspeak://library/"
_CAMSPEAK_PREVIEW_RE = re.compile(r"/api/library/[^/]+/[^/]+/preview$")

_STREAM_MIME_PREFIXES = (
    "audio/x-mpegurl",
    "audio/x-scpls",
    "application/x-mpegurl",
    "application/vnd.apple.mpegurl",
)
_STREAM_HINTS = ("liveatc.net", "/play/", "shoutcast", "icecast")
_STREAM_EXTENSIONS = (".pls", ".m3u", ".m3u8")

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_MEDIA_SOURCE_RE = re.compile(r"^media-source://")


def _media_source_domain(media_id: str) -> str | None:
    """Extract the domain from a media-source:// URI."""
    if not _MEDIA_SOURCE_RE.match(media_id):
        return None
    parts = media_id[len("media-source://") :].split("/", 1)
    return parts[0] if parts and parts[0] else None


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
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the media player."""
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{camera_name}_media_player"
        self._attr_name = "speaker"

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Overrides CoordinatorEntity.available to also consider camera online status.
        """
        if not self.coordinator.last_update_success:
            return False
        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            return False
        return data.cameras[self._camera_name].camera.get("online", False)

    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self) -> None:
        """Update entity state from coordinator data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            return

        cam_data = data.cameras[self._camera_name]
        cam = cam_data.camera
        playback = cam_data.playback

        if not cam.get("online", False):
            return

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
        - "url" or a URL with a file: download audio file, transcode, play
        - "stream" or a URL that looks like a live stream/playlist: stream
        - HA media-source:// URIs are resolved to a signed URL first
        """
        media_source_domain = _media_source_domain(media_id)
        if media_source_domain:
            sourced_media = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )
            media_id = async_process_play_media_url(self.hass, sourced_media.url)
            media_type = sourced_media.mime_type or MediaType.MUSIC
            # Some media sources are known to be live streams (e.g. Radio Browser)
            if media_source_domain == "radio_browser":
                await self.coordinator.client.play_stream(camera=self._camera_name, url=media_id)
                await self.coordinator.async_request_refresh()
                return
            # Camspeak media source returns a WAV preview URL for browser
            # playback. For camera playback, extract the preset name and
            # use play_preset directly (avoids download + transcode round-trip).
            if media_source_domain == DOMAIN and _CAMSPEAK_PREVIEW_RE.search(media_id):
                # URL is /api/library/<category>/<name>/preview — extract name
                preset_name = media_id.rstrip("/").rsplit("/", 2)[-2]
                await self.coordinator.client.play_preset(
                    camera=self._camera_name, preset=preset_name
                )
                await self.coordinator.async_request_refresh()
                return

        if media_id.startswith(_CAMSPEAK_PRESET_PREFIX):
            preset = media_id[len(_CAMSPEAK_PRESET_PREFIX) :]
            await self.coordinator.client.play_preset(camera=self._camera_name, preset=preset)
        elif _is_url(media_id):
            if _looks_like_stream(media_id, media_type):
                await self.coordinator.client.play_stream(camera=self._camera_name, url=media_id)
            else:
                await self.coordinator.client.play_url(camera=self._camera_name, url=media_id)
        else:
            await self.coordinator.client.play_preset(camera=self._camera_name, preset=media_id)
        await self.coordinator.async_request_refresh()

    @override
    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Return a BrowseMedia instance for the camspeak library."""
        if media_content_id and media_source.is_media_source_id(media_content_id):
            return await media_source.async_browse_media(
                self.hass,
                media_content_id,
                content_filter=_audio_content_filter,
            )

        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            return _root_browse([])

        presets = data.cameras[self._camera_name].presets

        if media_content_id and media_content_id.startswith(_CAMSPEAK_LIBRARY_PREFIX):
            category = media_content_id[len(_CAMSPEAK_LIBRARY_PREFIX) :]
            return _category_browse(category, presets)

        return _root_browse(presets, categories=data.categories)

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
        """Set volume level (maps to camera gain 0-10).

        Uses the dedicated volume endpoint which updates the runtime gain
        in real-time — the next audio chunk picks up the new volume without
        restarting playback.
        """
        gain = round(volume * 10, 1)
        await self.coordinator.client.set_volume(self._camera_name, gain)
        self._attr_volume_level = volume
        self.async_write_ha_state()


def _is_url(media_id: str) -> bool:
    """Return True if media_id is an http(s) URL."""
    return bool(_URL_RE.match(media_id))


def _looks_like_stream(media_id: str, media_type: str | None = None) -> bool:
    """Return True if media_id looks like a live stream or playlist."""
    if media_type:
        media_type_str = media_type.lower()
        if media_type_str == "stream" or media_type_str in _STREAM_MIME_PREFIXES:
            return True
        if media_type_str == MediaType.PLAYLIST:
            return True
    s = media_id.lower()
    return s.endswith(_STREAM_EXTENSIONS) or any(hint in s for hint in _STREAM_HINTS)


def _audio_content_filter(item: BrowseMedia) -> bool:
    """Filter HA media source items to audio."""
    return bool(item.media_content_type and item.media_content_type.startswith("audio/"))


def _preset_browse_item(preset: dict[str, Any]) -> BrowseMedia:
    """Return a BrowseMedia item for a camspeak preset."""
    name = preset["name"]
    title = f"{name} ({preset['duration']}s)" if preset.get("duration") else name
    return BrowseMedia(
        title=title,
        media_class=MediaClass.MUSIC,
        media_content_id=f"{_CAMSPEAK_PRESET_PREFIX}{name}",
        media_content_type=MediaType.MUSIC,
        can_play=True,
        can_expand=False,
    )


def _category_browse(category: str, presets: list[dict[str, Any]]) -> BrowseMedia:
    """Return a BrowseMedia instance for a category."""
    children = [
        _preset_browse_item(preset) for preset in presets if preset.get("category", "") == category
    ]
    return BrowseMedia(
        title=category.title() or "Camspeak Library",
        media_class=MediaClass.DIRECTORY,
        media_content_id=f"{_CAMSPEAK_LIBRARY_PREFIX}{category}",
        media_content_type=MediaType.MUSIC,
        can_play=False,
        can_expand=True,
        children=children,
    )


def _root_browse(
    presets: list[dict[str, Any]],
    categories: list[str] | None = None,
) -> BrowseMedia:
    """Return the root BrowseMedia instance for camspeak."""
    children: list[BrowseMedia]
    categories = categories or []

    if categories:
        children = [
            BrowseMedia(
                title=category.title(),
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{_CAMSPEAK_LIBRARY_PREFIX}{category}",
                media_content_type=MediaType.MUSIC,
                can_play=False,
                can_expand=True,
            )
            for category in categories
        ]
    else:
        children = [_preset_browse_item(preset) for preset in presets]

    return BrowseMedia(
        title="Camspeak Library",
        media_class=MediaClass.DIRECTORY,
        media_content_id="",
        media_content_type=MediaType.MUSIC,
        can_play=False,
        can_expand=True,
        children=children,
    )
