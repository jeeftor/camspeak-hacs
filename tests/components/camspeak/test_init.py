"""Tests for the camspeak init."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.camspeak.const import DOMAIN
from tests.common import MockConfigEntry

from . import setup_integration


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test loading and unloading the config entry."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.services.has_service(DOMAIN, "speak")
    assert hass.services.has_service(DOMAIN, "play_preset")
    assert hass.services.has_service(DOMAIN, "play_stream")
    assert hass.services.has_service(DOMAIN, "play_url")
    assert hass.services.has_service(DOMAIN, "broadcast")
    assert hass.services.has_service(DOMAIN, "beep")
    assert hass.services.has_service(DOMAIN, "stop")
    assert hass.services.has_service(DOMAIN, "pause")
    assert hass.services.has_service(DOMAIN, "resume")

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.services.has_service(DOMAIN, "speak")
    assert not hass.services.has_service(DOMAIN, "play_preset")


async def test_config_entry_not_ready(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test config entry not ready when camspeak is unreachable."""
    mock_camspeak_client.get_cameras.side_effect = Exception("connection refused")

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
