"""REST administration wrapper regression tests; no external services required."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.camspeak.api import CamspeakApiClient, _parse_response


@pytest.mark.parametrize(
    ("name", "method", "path", "arguments"),
    [
        ("get_config", "GET", "/api/config", []),
        ("get_settings", "GET", "/api/config/settings", []),
        ("update_settings", "PUT", "/api/config/settings", ["payload"]),
        ("test_settings", "POST", "/api/config/settings/test", ["payload"]),
        ("get_vision_config", "GET", "/api/config/vision", []),
        ("update_vision_config", "PUT", "/api/config/vision", ["payload"]),
        ("test_vision_config", "POST", "/api/config/vision/test", ["payload"]),
        ("get_vision_prompts", "GET", "/api/config/vision-prompts", []),
        ("save_vision_prompt", "POST", "/api/config/vision-prompts", ["payload"]),
        ("delete_vision_prompt", "DELETE", "/api/config/vision-prompts/name%2Ftest", ["name"]),
        ("get_tts_presets", "GET", "/api/config/tts", []),
        ("create_tts_preset", "POST", "/api/config/tts", ["payload"]),
        ("update_tts_preset", "PUT", "/api/config/tts/name%2Ftest", ["name", "payload"]),
        ("delete_tts_preset", "DELETE", "/api/config/tts/name%2Ftest", ["name"]),
        ("activate_tts_preset", "POST", "/api/config/tts/name%2Ftest/activate", ["name"]),
        ("reorder_cameras", "POST", "/api/config/cameras/reorder", ["payload"]),
        ("detect_camera", "POST", "/api/config/cameras/detect", ["payload"]),
        ("discover_cameras", "POST", "/api/config/cameras/discover", []),
        ("toggle_camera", "PATCH", "/api/config/cameras/name%2Ftest/toggle", ["name"]),
        ("delete_camera", "DELETE", "/api/config/cameras/name%2Ftest", ["name"]),
        ("get_go2rtc_streams", "GET", "/api/config/go2rtc/streams", []),
        ("get_airplay_config", "GET", "/api/config/airplay", []),
        ("update_airplay_config", "PUT", "/api/config/airplay", ["payload"]),
        ("toggle_camera_airplay", "PATCH", "/api/config/airplay/camera%2Ftest/toggle", ["camera"]),
        ("ping_camera", "POST", "/api/cameras/camera%2Ftest/ping", ["camera"]),
        ("get_camera_info", "GET", "/api/cameras/camera%2Ftest/info", ["camera"]),
        ("get_streams", "GET", "/api/streams", []),
        ("vision", "POST", "/api/vision", ["payload"]),
        ("test_vision", "POST", "/api/vision/test", ["payload"]),
        ("test_all_vision_models", "POST", "/api/vision/test-all", ["payload"]),
        ("describe", "POST", "/api/describe", ["payload"]),
        ("generate_preset", "POST", "/api/library", ["payload"]),
        ("get_upload_job", "GET", "/api/library/upload/jobs/name%2Ftest", ["name"]),
        (
            "delete_preset",
            "DELETE",
            "/api/library/category%2Ftest/name%2Ftest",
            ["category", "name"],
        ),
        (
            "rename_preset",
            "PATCH",
            "/api/library/category%2Ftest/name%2Ftest",
            ["category", "name", "payload"],
        ),
        (
            "get_preset_peaks",
            "GET",
            "/api/library/category%2Ftest/name%2Ftest/peaks",
            ["category", "name"],
        ),
        (
            "analyze_preset",
            "GET",
            "/api/library/category%2Ftest/name%2Ftest/analyze",
            ["category", "name"],
        ),
        (
            "set_preset_gain",
            "PUT",
            "/api/library/category%2Ftest/name%2Ftest/gain",
            ["category", "name", "payload"],
        ),
        ("get_openapi", "GET", "/api/openapi.json", []),
    ],
)
async def test_admin_route(name: str, method: str, path: str, arguments: list[str]) -> None:
    """Encode path identifiers and preserve request bodies without retries."""
    client = CamspeakApiClient("http://example.com", MagicMock())
    values = [{"test": True} if key == "payload" else key + "/test" for key in arguments]
    with patch.object(client, "_request", new_callable=AsyncMock) as request:
        await getattr(client, name)(*values)
        expected = {"json_data": {"test": True}} if "payload" in arguments else {}
        request.assert_awaited_once_with(method, path, **expected)


async def test_binary_response() -> None:
    """Do not decode image or audio bytes as text."""
    response = MagicMock(content_type="audio/wav")
    response.read = AsyncMock(return_value=b"RIFF")
    assert await _parse_response(response) == b"RIFF"
    response.text.assert_not_called()


@pytest.mark.parametrize(
    "method", ["stream_events", "stream_levels", "stream_benchmark", "stream_vision_comparison"]
)
async def test_stream_close_releases_response(method: str) -> None:
    """Closing a partially consumed public iterator must release its HTTP response."""

    async def chunks() -> AsyncIterator[bytes]:
        yield b"data: {}\n\n"
        yield b"data: {}\n\n"

    response = MagicMock(status=200, content_type="text/event-stream")
    response.content.iter_any.return_value = chunks()
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=response)
    manager.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.request.return_value = manager
    client = CamspeakApiClient("http://example.com", session)
    arguments = [{}] if method in ("stream_benchmark", "stream_vision_comparison") else []
    stream = getattr(client, method)(*arguments)
    assert await anext(stream) == b"data: {}\n\n"
    await stream.aclose()
    manager.__aexit__.assert_awaited_once()
    session.request.assert_called_once()
