"""Tests for the camspeak diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator

from . import setup_integration


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test diagnostics output."""
    await setup_integration(hass, mock_config_entry)

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, mock_config_entry)

    assert diagnostics["entry"]["host"] == "10.0.0.50"
    assert diagnostics["entry"]["port"] == 8585  # noqa: PLR2004
    assert diagnostics["entry"]["verify_ssl"] is False

    assert "backyard" in diagnostics["cameras"]
    assert diagnostics["cameras"]["backyard"]["online"] is True
    assert diagnostics["cameras"]["backyard"]["type"] == "hikvision"
    assert diagnostics["cameras"]["backyard"]["preset_count"] == 2  # noqa: PLR2004

    assert "frontyard" in diagnostics["cameras"]
    assert diagnostics["cameras"]["frontyard"]["online"] is True
