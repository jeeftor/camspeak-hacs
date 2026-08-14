"""Tests for the camspeak media player platform."""

from unittest.mock import AsyncMock

from homeassistant.components.media_player import (
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
