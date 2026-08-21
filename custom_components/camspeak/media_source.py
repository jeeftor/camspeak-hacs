"""Media Source implementation for the camspeak integration.

Exposes the camspeak preset library as a top-level browsable source in
Home Assistant's Media browser, so users can browse presets without first
selecting a specific camera entity. When a preset is selected, HA resolves
the media-source URI to a ``camspeak://preset/<name>`` URI, which the
media player's ``async_play_media`` already routes to ``play_preset``.
"""

from typing import Any

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CamspeakCoordinator

_CATEGORY_PREFIX = "category/"
_PRESET_PREFIX = "preset/"


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up camspeak media source."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise BrowseError("No camspeak config entries found")
    coordinator: CamspeakCoordinator = entries[0].runtime_data
    return CamspeakMediaSource(hass, coordinator)


class CamspeakMediaSource(MediaSource):
    """Represents the camspeak preset library as a media source."""

    name: str = "Camspeak"

    def __init__(self, hass: HomeAssistant, coordinator: CamspeakCoordinator) -> None:
        """Initialize the camspeak media source."""
        super().__init__(DOMAIN)
        self.hass = hass
        self.coordinator = coordinator

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a preset media item to a playable URI.

        Returns a ``camspeak://preset/<name>`` URI that the media player's
        ``async_play_media`` routes to the ``play_preset`` API call.
        """
        identifier = item.identifier or ""
        if not identifier.startswith(_PRESET_PREFIX):
            raise BrowseError(f"Unsupported camspeak media identifier: {identifier}")
        preset_name = identifier[len(_PRESET_PREFIX) :]
        return PlayMedia(
            f"camspeak://preset/{preset_name}",
            MediaType.MUSIC,
        )

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse the camspeak preset library."""
        data = self.coordinator.data
        if data is None:
            raise BrowseError("Camspeak data not yet loaded")

        presets = data.preset_names and _get_all_presets(self.coordinator)
        identifier = item.identifier

        if identifier is None or identifier == "":
            return self._browse_root(data.categories, presets)

        if identifier.startswith(_CATEGORY_PREFIX):
            category = identifier[len(_CATEGORY_PREFIX) :]
            return self._browse_category(category, presets)

        raise BrowseError(f"Unsupported camspeak media identifier: {identifier}")

    def _browse_root(
        self,
        categories: list[str],
        presets: list[dict[str, Any]],
    ) -> BrowseMediaSource:
        """Build the root browse node showing categories."""
        base = BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=self.name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
        )

        if categories:
            base.children = [
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{_CATEGORY_PREFIX}{category}",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.MUSIC,
                    title=category.title(),
                    can_play=False,
                    can_expand=True,
                    children_media_class=MediaClass.MUSIC,
                )
                for category in categories
            ]
        else:
            # No categories — show presets flat at the root.
            base.children = [self._preset_item(preset) for preset in presets]
            base.children_media_class = MediaClass.MUSIC

        return base

    def _browse_category(
        self,
        category: str,
        presets: list[dict[str, Any]],
    ) -> BrowseMediaSource:
        """Build a category browse node showing its presets."""
        children = [
            self._preset_item(preset)
            for preset in presets
            if preset.get("category", "") == category
        ]
        if not children:
            raise BrowseError(f"No presets found in category '{category}'")

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{_CATEGORY_PREFIX}{category}",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=category.title(),
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.MUSIC,
            children=children,
        )

    @staticmethod
    def _preset_item(preset: dict[str, Any]) -> BrowseMediaSource:
        """Build a browsable leaf node for a single preset."""
        name = preset["name"]
        duration = preset.get("duration")
        title = f"{name} ({duration}s)" if duration else name
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{_PRESET_PREFIX}{name}",
            media_class=MediaClass.MUSIC,
            media_content_type=MediaType.MUSIC,
            title=title,
            can_play=True,
            can_expand=False,
        )


def _get_all_presets(coordinator: CamspeakCoordinator) -> list[dict[str, Any]]:
    """Return the full preset list from the coordinator.

    Presets are stored per-camera in CameraData, but they are identical
    across all cameras (the library is global), so we take the first
    camera's preset list.
    """
    data = coordinator.data
    if data is None or not data.cameras:
        return []
    first_cam = next(iter(data.cameras.values()))
    return first_cam.presets
