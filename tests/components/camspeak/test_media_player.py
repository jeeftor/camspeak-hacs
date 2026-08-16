"""Tests for the camspeak media player platform."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.media_player import (
    DATA_COMPONENT,
    MediaPlayerState,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

from . import setup_integration

MEDIA_PLAYER_ENTITY = "media_player.backyard_speaker"


async def test_media_player_idle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media player in idle state."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state is not None
    assert state.state == MediaPlayerState.IDLE


async def test_media_player_playing(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media player in playing state."""
    mock_camspeak_client.get_playback.return_value = {
        "backyard": {
            "state": "playing",
            "source": "play",
            "detail": "rain",
        },
        "frontyard": {"state": "idle", "source": "", "detail": ""},
    }

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state.state == MediaPlayerState.PLAYING
    assert state.attributes.get("media_title") == "rain"


async def test_media_player_paused(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media player in paused state."""
    mock_camspeak_client.get_playback.return_value = {
        "backyard": {
            "state": "paused",
            "source": "stream",
            "detail": "http://stream.example.com/live",
        },
        "frontyard": {"state": "idle", "source": "", "detail": ""},
    }

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state.state == MediaPlayerState.PAUSED


async def test_media_player_volume(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media player volume from gain."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    # gain=3 → volume=0.3
    assert state.attributes.get("volume_level") == 0.3  # noqa: PLR2004


async def test_media_player_source_list(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media player source list from presets."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    sources = state.attributes.get("source_list")
    assert sources is not None
    assert "alert" in sources
    assert "rain" in sources


async def test_media_player_play_media_preset(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test playing a preset via play_media service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "media_content_type": "music",
            "media_content_id": "rain",
        },
        blocking=True,
    )
    mock_camspeak_client.play_preset.assert_called_once_with(camera="backyard", preset="rain")


async def test_media_player_play_media_url(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test playing a URL via play_media service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "media_content_type": "url",
            "media_content_id": "https://example.com/sound.mp3",
        },
        blocking=True,
    )
    mock_camspeak_client.play_url.assert_called_once_with(
        camera="backyard", url="https://example.com/sound.mp3"
    )


async def test_media_player_play_media_stream(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test playing a live stream via play_media service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "media_content_type": "stream",
            "media_content_id": "http://stream.example.com:8000/live",
        },
        blocking=True,
    )
    mock_camspeak_client.play_stream.assert_called_once_with(
        camera="backyard", url="http://stream.example.com:8000/live"
    )


async def test_media_player_pause(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test pausing playback."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "media_pause",
        {"entity_id": MEDIA_PLAYER_ENTITY},
        blocking=True,
    )
    mock_camspeak_client.pause.assert_called_once_with(camera="backyard")


async def test_media_player_play_resume_when_paused(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media_play resumes when state is paused."""
    mock_camspeak_client.get_playback.return_value = {
        "backyard": {
            "state": "paused",
            "source": "stream",
            "detail": "http://stream.example.com/live",
        },
        "frontyard": {"state": "idle", "source": "", "detail": ""},
    }

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state.state == MediaPlayerState.PAUSED

    await hass.services.async_call(
        "media_player",
        "media_play",
        {"entity_id": MEDIA_PLAYER_ENTITY},
        blocking=True,
    )
    mock_camspeak_client.resume.assert_called_once_with(camera="backyard")


async def test_media_player_play_does_nothing_when_idle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media_play does nothing when idle (no 404)."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state.state == MediaPlayerState.IDLE

    await hass.services.async_call(
        "media_player",
        "media_play",
        {"entity_id": MEDIA_PLAYER_ENTITY},
        blocking=True,
    )
    mock_camspeak_client.resume.assert_not_called()


async def test_media_player_stop(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test stopping playback."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "media_stop",
        {"entity_id": MEDIA_PLAYER_ENTITY},
        blocking=True,
    )
    mock_camspeak_client.stop.assert_called_once_with(camera="backyard")


async def test_media_player_select_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test selecting a source (preset)."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": MEDIA_PLAYER_ENTITY, "source": "alert"},
        blocking=True,
    )
    mock_camspeak_client.play_preset.assert_called_once_with(camera="backyard", preset="alert")


async def test_media_player_set_volume(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test setting volume level calls the volume API endpoint."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "volume_set",
        {"entity_id": MEDIA_PLAYER_ENTITY, "volume_level": 0.5},
        blocking=True,
    )
    mock_camspeak_client.set_volume.assert_called_once()
    call_args = mock_camspeak_client.set_volume.call_args
    assert call_args.args[0] == "backyard"
    assert call_args.args[1] == 5.0  # noqa: PLR2004
    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state.attributes.get("volume_level") == 0.5  # noqa: PLR2004


async def test_media_player_unavailable_when_offline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test media player is unavailable when camera is offline."""
    mock_camspeak_client.get_cameras.return_value = [
        {"name": "backyard", "type": "hikvision", "online": False, "ip": "10.0.0.50"},
        {"name": "frontyard", "type": "hikvision", "online": True, "ip": "10.0.0.51"},
    ]

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(MEDIA_PLAYER_ENTITY)
    assert state.state == STATE_UNAVAILABLE


def _get_media_player_entity(hass: HomeAssistant) -> Any:
    """Return the camspeak media player entity."""
    return hass.data[DATA_COMPONENT].get_entity(MEDIA_PLAYER_ENTITY)


async def test_media_player_browse_media_root(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test browsing the camspeak library root returns categories."""
    await setup_integration(hass, mock_config_entry)

    entity = _get_media_player_entity(hass)
    result = await entity.async_browse_media()

    assert result.title == "Camspeak Library"
    assert len(result.children) == 2  # noqa: PLR2004
    assert result.children[0].title == "Default"
    assert result.children[0].media_content_id == "camspeak://library/default"
    assert result.children[1].title == "Uploads"


async def test_media_player_browse_media_category(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test browsing a category returns its presets."""
    await setup_integration(hass, mock_config_entry)

    entity = _get_media_player_entity(hass)
    result = await entity.async_browse_media(media_content_id="camspeak://library/uploads")

    assert result.title == "Uploads"
    assert len(result.children) == 1
    assert result.children[0].title == "rain (15.9s)"
    assert result.children[0].media_content_id == "camspeak://preset/rain"
    assert result.children[0].can_play is True
    assert result.children[0].can_expand is False


async def test_media_player_play_media_url_from_music(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that a URL sent as music type is routed to play_url."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "media_content_type": "music",
            "media_content_id": "https://example.com/sound.mp3",
        },
        blocking=True,
    )
    mock_camspeak_client.play_url.assert_called_once_with(
        camera="backyard", url="https://example.com/sound.mp3"
    )
    mock_camspeak_client.play_stream.assert_not_called()


async def test_media_player_play_media_stream_auto(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that a .m3u URL is auto-routed to play_stream."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "media_content_type": "url",
            "media_content_id": "http://stream.example.com/playlist.m3u",
        },
        blocking=True,
    )
    mock_camspeak_client.play_stream.assert_called_once_with(
        camera="backyard", url="http://stream.example.com/playlist.m3u"
    )
    mock_camspeak_client.play_url.assert_not_called()


async def test_media_player_play_media_camspeak_preset(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that a camspeak://preset/ URI is routed to play_preset."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "media_content_type": "music",
            "media_content_id": "camspeak://preset/rain",
        },
        blocking=True,
    )
    mock_camspeak_client.play_preset.assert_called_once_with(camera="backyard", preset="rain")


async def test_media_player_play_media_media_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that a media-source:// URI is resolved and routed to play_url."""
    await setup_integration(hass, mock_config_entry)

    resolved = MagicMock()
    resolved.url = "/media/song.mp3"
    resolved.mime_type = "audio/mpeg"

    with (
        patch(
            "custom_components.camspeak.media_player.media_source.is_media_source_id",
            return_value=True,
        ),
        patch(
            "custom_components.camspeak.media_player.media_source.async_resolve_media",
            new_callable=AsyncMock,
            return_value=resolved,
        ) as mock_resolve,
        patch(
            "custom_components.camspeak.media_player.async_process_play_media_url",
            return_value="http://ha:8123/media/song.mp3",
        ),
    ):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": MEDIA_PLAYER_ENTITY,
                "media_content_type": "audio/mpeg",
                "media_content_id": "media-source://media_source/local/song.mp3",
            },
            blocking=True,
        )
        mock_resolve.assert_awaited_once()

    mock_camspeak_client.play_url.assert_called_once_with(
        camera="backyard", url="http://ha:8123/media/song.mp3"
    )


async def test_media_player_play_media_radio_browser(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that a media-source://radio_browser/ URI is routed to play_stream."""
    await setup_integration(hass, mock_config_entry)

    resolved = MagicMock()
    resolved.url = "http://stream.example.com:8000/live"
    resolved.mime_type = "audio/mpeg"

    with (
        patch(
            "custom_components.camspeak.media_player.media_source.async_resolve_media",
            new_callable=AsyncMock,
            return_value=resolved,
        ),
        patch(
            "custom_components.camspeak.media_player.async_process_play_media_url",
            return_value="http://stream.example.com:8000/live",
        ),
    ):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": MEDIA_PLAYER_ENTITY,
                "media_content_type": "audio/mpeg",
                "media_content_id": "media-source://radio_browser/abc-123",
            },
            blocking=True,
        )

    mock_camspeak_client.play_stream.assert_called_once_with(
        camera="backyard", url="http://stream.example.com:8000/live"
    )
