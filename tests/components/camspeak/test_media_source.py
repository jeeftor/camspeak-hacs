"""Tests for the camspeak media_source platform."""

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    DOMAIN as MS_DOMAIN,
    async_browse_media,
    async_resolve_media,
    generate_media_source_id,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from tests.common import MockConfigEntry

from . import setup_integration


async def test_media_source_browse_root(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client,
) -> None:
    """Test browsing the root returns categories."""
    await setup_integration(hass, mock_config_entry)
    assert await async_setup_component(hass, MS_DOMAIN, {})
    await hass.async_block_till_done()

    result = await async_browse_media(hass, generate_media_source_id("camspeak", ""))

    assert result.title == "Camspeak"
    assert result.can_expand is True
    assert result.can_play is False
    assert len(result.children) == 2  # noqa: PLR2004
    titles = [c.title for c in result.children]
    assert "Default" in titles
    assert "Uploads" in titles
    assert all(c.can_expand for c in result.children)
    assert all(not c.can_play for c in result.children)


async def test_media_source_browse_category(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client,
) -> None:
    """Test browsing a category returns its presets."""
    await setup_integration(hass, mock_config_entry)
    assert await async_setup_component(hass, MS_DOMAIN, {})
    await hass.async_block_till_done()

    result = await async_browse_media(
        hass, generate_media_source_id("camspeak", "category/uploads")
    )

    assert result.title == "Uploads"
    assert result.can_expand is True
    assert len(result.children) == 1
    child = result.children[0]
    assert child.title == "rain (15.9s)"
    assert child.can_play is True
    assert child.can_expand is False
    assert child.media_class == MediaClass.MUSIC
    assert child.media_content_type == MediaType.MUSIC


async def test_media_source_resolve_preset(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client,
) -> None:
    """Test resolving a preset returns a camspeak://preset/ URI."""
    await setup_integration(hass, mock_config_entry)
    assert await async_setup_component(hass, MS_DOMAIN, {})
    await hass.async_block_till_done()

    play_media = await async_resolve_media(
        hass, generate_media_source_id("camspeak", "preset/rain"), None
    )

    assert play_media.url == "camspeak://preset/rain"
    assert play_media.mime_type == MediaType.MUSIC


async def test_media_source_browse_invalid_identifier(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client,
) -> None:
    """Test browsing an invalid identifier raises BrowseError."""
    await setup_integration(hass, mock_config_entry)
    assert await async_setup_component(hass, MS_DOMAIN, {})
    await hass.async_block_till_done()

    with pytest.raises(BrowseError):
        await async_browse_media(hass, generate_media_source_id("camspeak", "invalid/path"))


async def test_media_source_resolve_invalid_identifier(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client,
) -> None:
    """Test resolving a non-preset identifier raises BrowseError."""
    await setup_integration(hass, mock_config_entry)
    assert await async_setup_component(hass, MS_DOMAIN, {})
    await hass.async_block_till_done()

    with pytest.raises(BrowseError):
        await async_resolve_media(
            hass, generate_media_source_id("camspeak", "category/uploads"), None
        )


async def test_media_source_browse_empty_category(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_camspeak_client,
) -> None:
    """Test browsing a category with no presets raises BrowseError."""
    await setup_integration(hass, mock_config_entry)
    assert await async_setup_component(hass, MS_DOMAIN, {})
    await hass.async_block_till_done()

    with pytest.raises(BrowseError):
        await async_browse_media(hass, generate_media_source_id("camspeak", "category/nonexistent"))
