"""TTS platform for the camspeak integration.

Exposes the camspeak TTS engine as a Home Assistant TTS entity so it can be
used from the ``tts.speak`` service on any media player (not just cameras).
The camspeak server's ``POST /api/tts/preview`` endpoint generates WAV audio
from text + voice, which this entity returns to HA's TTS framework.
"""

from collections.abc import Mapping
from typing import Any, override

from homeassistant.components.tts import (
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from propcache.api import cached_property

from .api import CamspeakApiClientError
from .const import DOMAIN
from .coordinator import CamspeakCoordinator

# Camspeak's TTS engine (Kokoro) is multilingual; the server doesn't expose
# a language list, so we advertise a broad set of supported languages.
# The voice option is what actually controls the output.
_SUPPORTED_LANGUAGES = [
    "en-US",
    "en-GB",
    "es-ES",
    "fr-FR",
    "de-DE",
    "it-IT",
    "pt-BR",
    "pl-PL",
    "nl-NL",
    "ro-RO",
    "ja-JP",
    "zh-CN",
    "ko-KR",
    "hi-IN",
    "af-ZA",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[CamspeakCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up camspeak TTS entity from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([CamspeakTTSEntity(coordinator)])


class CamspeakTTSEntity(TextToSpeechEntity):
    """Camspeak TTS engine entity."""

    _attr_has_entity_name = False
    _attr_supported_languages = _SUPPORTED_LANGUAGES
    _attr_default_language = "en-US"
    _attr_supported_options = (ATTR_VOICE,)

    def __init__(self, coordinator: CamspeakCoordinator) -> None:
        """Initialize the TTS entity."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_tts"
        self._attr_name = f"{DOMAIN.title()} TTS"

    @override
    @cached_property
    def default_options(self) -> Mapping[str, Any]:
        """Return default options — first available voice."""
        voices = self._get_voices()
        default_voice = voices[0] if voices else ""
        return {ATTR_VOICE: default_voice}

    @override
    def async_get_supported_voices(self, language: str) -> list[Voice] | None:
        """Return the list of voices from the camspeak server."""
        voices = self._get_voices()
        if not voices:
            return None
        return [Voice(voice, voice) for voice in voices]

    @override
    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Generate TTS audio via the camspeak server."""
        voice = options.get(ATTR_VOICE, "")
        if not voice:
            voices = self._get_voices()
            voice = voices[0] if voices else ""

        try:
            wav_data = await self.coordinator.client.tts_preview(text=message, voice=voice)
        except CamspeakApiClientError as exc:
            raise HomeAssistantError(f"camspeak TTS failed: {exc}") from exc

        return "wav", wav_data

    def _get_voices(self) -> list[str]:
        """Return the current voice list from coordinator data."""
        data = self.coordinator.data
        if data is None:
            return []
        return data.voices
