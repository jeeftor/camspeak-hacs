"""Tests for the camspeak sensor platform."""

from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, async_fire_time_changed

from . import setup_integration

PLAYBACK_ENTITY = "sensor.backyard_playback"
ONLINE_ENTITY = "binary_sensor.backyard_online"


async def test_playback_sensor_idle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test playback sensor in idle state."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(PLAYBACK_ENTITY)
    assert state is not None
    assert state.state == "idle"
    assert state.attributes["source"] == ""
    assert state.attributes["detail"] == ""


async def test_playback_sensor_playing(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test playback sensor in playing state."""
    mock_camspeak_client.get_playback.return_value = {
        "backyard": {
            "state": "playing",
            "source": "play",
            "detail": "rain",
            "started": "2026-01-01T00:00:00Z",
        },
        "frontyard": {"state": "idle", "source": "", "detail": ""},
    }

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(PLAYBACK_ENTITY)
    assert state.state == "playing"
    assert state.attributes["source"] == "play"
    assert state.attributes["detail"] == "rain"
    assert state.attributes["started"] == "2026-01-01T00:00:00Z"


async def test_playback_sensor_paused(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test playback sensor in paused state."""
    mock_camspeak_client.get_playback.return_value = {
        "backyard": {
            "state": "paused",
            "source": "stream",
            "detail": "http://stream.example.com/live",
            "started": "2026-01-01T00:00:00Z",
            "paused_at": "2026-01-01T00:05:00Z",
        },
        "frontyard": {"state": "idle", "source": "", "detail": ""},
    }

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(PLAYBACK_ENTITY)
    assert state.state == "paused"
    assert state.attributes["source"] == "stream"
    assert state.attributes["paused_at"] == "2026-01-01T00:05:00Z"


async def test_online_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test online sensor."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ONLINE_ENTITY)
    assert state is not None
    assert state.state == "on"


async def test_online_sensor_offline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test online sensor when camera is offline."""
    mock_camspeak_client.get_cameras.return_value = [
        {"name": "backyard", "type": "hikvision", "online": False, "ip": "10.0.0.50"},
        {"name": "frontyard", "type": "hikvision", "online": True, "ip": "10.0.0.51"},
    ]

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ONLINE_ENTITY)
    assert state.state == "off"


async def test_sensor_unavailable_on_connection_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client: AsyncMock,
    freezer,
) -> None:
    """Test sensor becomes unavailable on connection error."""
    await setup_integration(hass, mock_config_entry)

    # Simulate connection error on next update
    mock_camspeak_client.get_cameras.side_effect = Exception("connection lost")
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(PLAYBACK_ENTITY)
    assert state.state == STATE_UNAVAILABLE
