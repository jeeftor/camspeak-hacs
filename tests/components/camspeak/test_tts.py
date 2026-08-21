"""Tests for the camspeak TTS platform."""

from typing import Any
from unittest.mock import AsyncMock

from homeassistant.components.tts import ATTR_VOICE, DATA_COMPONENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry

from . import setup_integration

TTS_ENTITY = "tts.camspeak_tts"


async def test_tts_entity_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that the TTS entity is created on setup."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(TTS_ENTITY)
    assert state is not None


async def test_tts_supported_voices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test that supported voices come from the coordinator."""
    await setup_integration(hass, mock_config_entry)

    entity = _get_tts_entity(hass)
    voices = entity.async_get_supported_voices("en-US")
    assert voices is not None
    voice_ids = [v.voice_id for v in voices]
    assert "af_sky" in voice_ids
    assert "am_adam" in voice_ids


async def test_tts_default_options(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test default options include the first voice."""
    await setup_integration(hass, mock_config_entry)

    entity = _get_tts_entity(hass)
    default_opts = entity.default_options
    assert ATTR_VOICE in default_opts
    # First voice from conftest mock: af_sky
    assert default_opts[ATTR_VOICE] == "af_sky"


async def test_tts_get_tts_audio(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test generating TTS audio calls the API client."""
    mock_camspeak_client.tts_preview.return_value = b"WAV_DATA"
    await setup_integration(hass, mock_config_entry)

    entity = _get_tts_entity(hass)
    extension, data = await entity.async_get_tts_audio(
        "Hello world", "en-US", {ATTR_VOICE: "am_adam"}
    )

    assert extension == "wav"
    assert data == b"WAV_DATA"
    mock_camspeak_client.tts_preview.assert_called_once_with(text="Hello world", voice="am_adam")


async def test_tts_get_tts_audio_default_voice(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test TTS uses default voice when none specified."""
    mock_camspeak_client.tts_preview.return_value = b"WAV_DATA"
    await setup_integration(hass, mock_config_entry)

    entity = _get_tts_entity(hass)
    extension, data = await entity.async_get_tts_audio("Hello world", "en-US", {})

    assert extension == "wav"
    assert data == b"WAV_DATA"
    mock_camspeak_client.tts_preview.assert_called_once_with(text="Hello world", voice="af_sky")


async def test_tts_unique_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test the TTS entity has a stable unique ID."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(TTS_ENTITY)
    assert entry is not None
    assert entry.unique_id == f"{mock_config_entry.entry_id}_tts"


def _get_tts_entity(hass: HomeAssistant) -> Any:
    """Return the camspeak TTS entity instance."""
    return hass.data[DATA_COMPONENT].get_entity(TTS_ENTITY)
