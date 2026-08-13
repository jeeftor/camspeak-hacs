"""Tests for camspeak services."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

from . import setup_integration


async def test_speak_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the speak service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "speak",
        {
            "camera": "backyard",
            "text": "Person detected",
            "voice": "af_sky",
            "gain": 5.0,
        },
        blocking=True,
    )
    mock_camspeak_client.speak.assert_called_once_with(
        camera="backyard",
        text="Person detected",
        voice="af_sky",
        gain=5.0,
    )


async def test_play_preset_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the play_preset service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "play_preset",
        {
            "camera": "backyard",
            "preset": "rain",
            "category": "uploads",
            "loop": True,
        },
        blocking=True,
    )
    mock_camspeak_client.play_preset.assert_called_once_with(
        camera="backyard",
        preset="rain",
        category="uploads",
        gain=0,
        loop=True,
    )


async def test_play_stream_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the play_stream service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "play_stream",
        {"camera": "backyard", "url": "http://stream.example.com/live"},
        blocking=True,
    )
    mock_camspeak_client.play_stream.assert_called_once_with(
        camera="backyard", url="http://stream.example.com/live"
    )


async def test_play_url_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the play_url service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "play_url",
        {"camera": "backyard", "url": "https://example.com/sound.mp3"},
        blocking=True,
    )
    mock_camspeak_client.play_url.assert_called_once_with(
        camera="backyard", url="https://example.com/sound.mp3"
    )


async def test_broadcast_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the broadcast service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "broadcast",
        {"text": "Attention all cameras", "voice": "af_sky"},
        blocking=True,
    )
    mock_camspeak_client.broadcast.assert_called_once_with(
        text="Attention all cameras",
        preset="",
        voice="af_sky",
        gain=0,
    )


async def test_beep_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the beep service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "beep",
        {"camera": "backyard"},
        blocking=True,
    )
    mock_camspeak_client.beep.assert_called_once_with(camera="backyard")


async def test_stop_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the stop service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "stop",
        {"camera": "backyard"},
        blocking=True,
    )
    mock_camspeak_client.stop.assert_called_once_with(camera="backyard")


async def test_stop_all_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the stop service without camera (stops all)."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "stop",
        {},
        blocking=True,
    )
    mock_camspeak_client.stop.assert_called_once_with(camera="")


async def test_pause_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the pause service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "pause",
        {"camera": "backyard"},
        blocking=True,
    )
    mock_camspeak_client.pause.assert_called_once_with(camera="backyard")


async def test_resume_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the resume service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "camspeak",
        "resume",
        {"camera": "backyard"},
        blocking=True,
    )
    mock_camspeak_client.resume.assert_called_once_with(camera="backyard")
