"""Tests for camspeak services."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from tests.common import MockConfigEntry

from . import setup_integration

MEDIA_PLAYER_ENTITY = "media_player.backyard_speaker"


async def test_speak_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the speak service returns timing data."""
    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        "camspeak",
        "speak",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "text": "Person detected",
            "voice": "af_sky",
            "gain": 5.0,
        },
        blocking=True,
        return_response=True,
    )
    mock_camspeak_client.speak.assert_called_once_with(
        camera="backyard",
        text="Person detected",
        voice="af_sky",
        gain=5.0,
    )
    assert "cameras" in response
    assert response["cameras"]["backyard"]["status"] == "ok"


async def test_speak_no_target_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test speak raises if no camera target specified."""
    await setup_integration(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError, match="No cameras selected"):
        await hass.services.async_call(
            "camspeak",
            "speak",
            {"text": "Hello"},
            blocking=True,
        )


async def test_play_preset_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the play_preset service."""
    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        "camspeak",
        "play_preset",
        {
            "entity_id": MEDIA_PLAYER_ENTITY,
            "preset": "rain",
            "category": "uploads",
            "loop": True,
        },
        blocking=True,
        return_response=True,
    )
    mock_camspeak_client.play_preset.assert_called_once_with(
        camera="backyard",
        preset="rain",
        category="uploads",
        gain=0,
        loop=True,
    )
    assert response["cameras"]["backyard"]["status"] == "ok"


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
        {"entity_id": MEDIA_PLAYER_ENTITY, "url": "http://stream.example.com/live"},
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
        {"entity_id": MEDIA_PLAYER_ENTITY, "url": "https://example.com/sound.mp3"},
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
    """Test the broadcast service returns succeeded cameras."""
    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        "camspeak",
        "broadcast",
        {"text": "Attention all cameras", "voice": "af_sky"},
        blocking=True,
        return_response=True,
    )
    mock_camspeak_client.broadcast.assert_called_once_with(
        text="Attention all cameras",
        preset="",
        voice="af_sky",
        gain=0,
    )
    assert response["status"] == "ok"
    assert "backyard" in response["succeeded"]


async def test_broadcast_no_text_or_preset_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test broadcast raises if neither text nor preset is provided."""
    await setup_integration(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError, match="Either text or preset"):
        await hass.services.async_call(
            "camspeak",
            "broadcast",
            {},
            blocking=True,
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
        {"entity_id": MEDIA_PLAYER_ENTITY},
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
        {"entity_id": MEDIA_PLAYER_ENTITY},
        blocking=True,
    )
    mock_camspeak_client.stop.assert_called_once_with(camera="backyard")


async def test_stop_all_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the stop service without entity_id (stops all)."""
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
        {"entity_id": MEDIA_PLAYER_ENTITY},
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
        {"entity_id": MEDIA_PLAYER_ENTITY},
        blocking=True,
    )
    mock_camspeak_client.resume.assert_called_once_with(camera="backyard")
