"""Test fixtures for camspeak."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.camspeak.const import CONF_URL, CONF_VERIFY_SSL, DOMAIN
from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.camspeak.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_camspeak_client() -> Generator[AsyncMock]:
    """Mock the camspeak API client."""
    with (
        patch(
            "custom_components.camspeak.CamspeakApiClient",
            autospec=True,
        ) as mock_client,
        patch(
            "custom_components.camspeak.config_flow.CamspeakApiClient",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value
        client.health.return_value = {"status": "ok", "version": "1.0.0"}
        client.get_cameras.return_value = [
            {"name": "backyard", "type": "hikvision", "online": True, "ip": "10.0.0.50"},
            {"name": "frontyard", "type": "hikvision", "online": True, "ip": "10.0.0.51"},
        ]
        client.get_config_cameras.return_value = [
            {
                "name": "backyard",
                "type": "hikvision",
                "gain": 3,
                "ip": "10.0.0.50",
                "channel": 1,
                "stream": "backyard",
            },
            {
                "name": "frontyard",
                "type": "hikvision",
                "gain": 3,
                "ip": "10.0.0.51",
                "channel": 1,
                "stream": "frontyard",
            },
        ]
        client.get_playback.return_value = {
            "backyard": {"state": "idle", "source": "", "detail": ""},
            "frontyard": {"state": "idle", "source": "", "detail": ""},
        }
        client.get_library.return_value = [
            {"name": "alert", "category": "default", "duration": 2.5},
            {"name": "rain", "category": "uploads", "duration": 15.9},
        ]
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="camspeak (http://10.0.0.50:8585)",
        data={
            CONF_URL: "http://10.0.0.50:8585",
            CONF_VERIFY_SSL: False,
        },
        unique_id="http://10.0.0.50:8585",
    )
