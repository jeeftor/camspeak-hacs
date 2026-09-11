"""Regression tests for the camspeak playback API contract."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.media_player import MediaPlayerEntityFeature, MediaPlayerState
import pytest

from custom_components.camspeak.api import CamspeakApiClient
from custom_components.camspeak.coordinator import CameraData, CamspeakData
from custom_components.camspeak.media_player import CamspeakMediaPlayer, _preset_browse_item


async def test_tts_model_catalog_contract() -> None:
    """Pass the exact selected model without playing or loading it."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await client.test_tts_model("http://example.com/v1/audio/speech", "kokoro-v1")
        request.assert_awaited_once_with(
            "POST",
            "/api/config/tts/test",
            {"url": "http://example.com/v1/audio/speech", "model": "kokoro-v1", "api_key": ""},
        )


async def test_capture_source_pair() -> None:
    """Preserve camera settings while changing method and stream together."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    camera = {"name": "front", "gain": 2, "vision_stream": "old"}
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await client.update_camera_capture(camera, "isapi", "main")
        request.assert_awaited_once_with(
            "POST",
            "/api/config/cameras",
            json_data={"name": "front", "gain": 2, "snap_method": "isapi", "vision_stream": "main"},
        )
    assert camera["vision_stream"] == "old"


async def test_speaker_benchmark_job_contract() -> None:
    """Require caller confirmation and keep polling/cancellation separate from playback."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await client.start_speaker_benchmark("front", "local", "hello", confirm_playback=True)
        assert request.call_args.args[0:2] == ("POST", "/api/config/tts/benchmark/speaker")
        assert request.call_args.args[2]["confirm_playback"] is True
        await client.get_speaker_benchmark("job/one")
        request.assert_awaited_with("GET", "/api/config/tts/benchmark/jobs/job%2Fone")
        await client.cancel_speaker_benchmark("job/one")
        request.assert_awaited_with("DELETE", "/api/config/tts/benchmark/jobs/job%2Fone")


async def test_benchmark_tts_contract() -> None:
    """Send explicit transport and PCM parameters without touching playback."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await client.benchmark_tts("local", "streaming", "test")
        request.assert_awaited_once_with(
            "POST",
            "/api/config/tts/benchmark",
            {
                "preset": "local",
                "mode": "streaming",
                "text": "test",
                "voice": "",
                "sample_rate": 24000,
                "channels": 1,
            },
        )


async def test_get_events_preserves_replay_metadata() -> None:
    """Keep legacy records and new replay options intact when reading history."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    events = [
        {"camera": "front", "action": "play", "text": "Legacy"},
        {
            "id": 2,
            "camera": "Front & Back",
            "action": "play",
            "replay": {
                "method": "POST",
                "path": "/api/play",
                "body": {"camera": "Front & Back", "preset": "Alert", "gain": 0, "loop": -1},
            },
        },
    ]
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        request.return_value = events
        result = await client.get_events(limit=20, camera="Front & Back")
        request.assert_awaited_once_with("GET", "/api/events/log?limit=20&camera=Front+%26+Back")
    assert result == events


async def test_get_events_defaults() -> None:
    """Request recent history without adding an empty camera filter."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await client.get_events()
        request.assert_awaited_once_with("GET", "/api/events/log?limit=100")


@pytest.mark.parametrize(
    ("method", "arguments"),
    [
        ("speak", {"camera": "backyard", "text": "Hello"}),
        ("play_preset", {"camera": "backyard", "preset": "rain", "category": "uploads"}),
        ("play_url", {"camera": "backyard", "url": "https://example.com/audio.wav"}),
        ("play_stream", {"camera": "backyard", "url": "https://example.com/live"}),
        ("announce", {"source_camera": "frontyard", "target_camera": "backyard"}),
        ("start_describe_job", {"camera": "backyard"}),
        ("broadcast", {"preset": "rain", "category": "uploads"}),
    ],
)
@pytest.mark.parametrize("gain", [None, 0.0, 2.0])
async def test_gain_contract(method: str, arguments: dict[str, Any], gain: float | None) -> None:
    """Omit inherited gain and preserve an explicit mute across playback methods."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await getattr(client, method)(**arguments, gain=gain)
    payload = request.call_args.kwargs["json_data"]
    if gain is None:
        assert "gain" not in payload
    else:
        assert payload["gain"] == gain
    if "category" in arguments:
        assert payload["category"] == arguments["category"]


async def test_start_describe_job_contract() -> None:
    """Return the accepted job without holding a request open through playback."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    accepted = {
        "id": "describe-123",
        "camera": "backyard",
        "status": "running",
        "stage": "snapshot",
        "elapsed_ms": 0,
        "result": {},
    }
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        request.return_value = accepted
        result = await client.start_describe_job(
            "backyard", prompt="Describe visitors", stream="substream", gain=0
        )
        request.assert_awaited_once_with(
            "POST",
            "/api/describe/jobs",
            json_data={
                "camera": "backyard",
                "prompt": "Describe visitors",
                "stream": "substream",
                "gain": 0,
            },
        )
    assert result == accepted


async def test_start_describe_job_defaults() -> None:
    """Leave optional settings omitted so your camera and server defaults apply."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await client.start_describe_job("backyard")
        request.assert_awaited_once_with(
            "POST", "/api/describe/jobs", json_data={"camera": "backyard"}
        )


@pytest.mark.parametrize("status", ["running", "done", "error", "canceled"])
async def test_get_describe_job_contract(status: str) -> None:
    """Preserve progress, partial results, timings, and errors in job snapshots."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    job = {
        "id": "describe-123",
        "camera": "backyard",
        "status": status,
        "stage": "connecting" if status == "running" else status,
        "elapsed_ms": 3000,
        "result": {"description": "A visitor", "timings": {"vision_ms": 2000}},
        "error": "Camera unavailable" if status == "error" else "",
    }
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        request.return_value = job
        result = await client.get_describe_job("describe-123")
        request.assert_awaited_once_with("GET", "/api/describe/jobs/describe-123")
    assert result == job


@pytest.fixture
def contract_player() -> CamspeakMediaPlayer:
    """Build a player with isolated coordinator data and no platform setup."""
    coordinator = MagicMock()
    coordinator.client = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.data = CamspeakData(
        cameras={
            "backyard": CameraData(
                camera={"online": True, "gain": 0},
                playback={"state": "preparing", "can_pause": False},
                presets=[
                    {"name": "rain", "category": "uploads"},
                    {"name": "rain", "category": "weather"},
                ],
                preset_names=["uploads/rain", "weather/rain"],
            )
        },
        voices=[],
        preset_names=["uploads/rain", "weather/rain"],
        categories=["uploads", "weather"],
    )
    return CamspeakMediaPlayer(coordinator, "backyard")


def test_preparing_mute_and_pause_capability(contract_player: CamspeakMediaPlayer) -> None:
    """Show preparation and mute accurately and restore pause when supported."""
    contract_player._update_state()  # noqa: SLF001
    assert contract_player.state == MediaPlayerState.BUFFERING
    assert contract_player.volume_level == 0
    assert not contract_player.supported_features & MediaPlayerEntityFeature.PAUSE
    contract_player.coordinator.data.cameras["backyard"].playback = {
        "state": "playing",
        "can_pause": True,
        "detail": "rain",
    }
    contract_player._update_state()  # noqa: SLF001
    assert contract_player.supported_features & MediaPlayerEntityFeature.PAUSE
    assert contract_player.media_title == "rain"
    contract_player.coordinator.data.cameras["backyard"].playback = {"state": "idle"}
    contract_player._update_state()  # noqa: SLF001
    assert contract_player.media_title is None


async def test_duplicate_preset_identity(contract_player: CamspeakMediaPlayer) -> None:
    """Round-trip category-qualified browser IDs and duplicate source labels."""
    item = _preset_browse_item({"name": "rain", "category": "weather"})
    assert item.media_content_id == "camspeak://preset/weather/rain"
    await contract_player.async_play_media("music", item.media_content_id)
    contract_player.coordinator.client.play_preset.assert_awaited_once_with(
        camera="backyard", preset="rain", category="weather"
    )
    contract_player.coordinator.client.play_preset.reset_mock()
    await contract_player.async_select_source("uploads/rain")
    contract_player.coordinator.client.play_preset.assert_awaited_once_with(
        camera="backyard", preset="rain", category="uploads"
    )
