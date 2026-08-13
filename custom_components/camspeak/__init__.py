"""The camspeak Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CamspeakApiClient
from .const import DOMAIN, PLATFORMS
from .coordinator import CamspeakCoordinator

_LOGGER = logging.getLogger(__name__)

type CamspeakConfigEntry = ConfigEntry[CamspeakCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CamspeakConfigEntry) -> bool:
    """Set up camspeak from a config entry."""
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)
    scheme = "https" if verify_ssl else "http"
    base_url = f"{scheme}://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"

    client = CamspeakApiClient(
        base_url,
        verify_ssl=verify_ssl,
        session=async_get_clientsession(hass, verify_ssl=verify_ssl),
    )

    coordinator = CamspeakCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: CamspeakConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = entry.runtime_data
        await coordinator.client.close()
    return unload_ok


async def _async_register_services(
    hass: HomeAssistant, coordinator: CamspeakCoordinator
) -> None:
    """Register camspeak services."""
    import voluptuous as vol

    from .const import (
        SERVICE_BEEP,
        SERVICE_BROADCAST,
        SERVICE_PAUSE,
        SERVICE_PLAY_PRESET,
        SERVICE_PLAY_STREAM,
        SERVICE_PLAY_URL,
        SERVICE_RESUME,
        SERVICE_SPEAK,
        SERVICE_STOP,
    )

    client = coordinator.client

    def _get_camera(service_call) -> str:
        """Extract camera name from service call."""
        return service_call.data.get("camera", "")

    hass.services.async_register(
        DOMAIN,
        SERVICE_SPEAK,
        lambda call: _async_speak(hass, client, call),
        schema=vol.Schema(
            {
                vol.Required("camera"): str,
                vol.Required("text"): str,
                vol.Optional("voice"): str,
                vol.Optional("gain"): vol.Coerce(float),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_PRESET,
        lambda call: _async_play_preset(hass, client, call),
        schema=vol.Schema(
            {
                vol.Required("camera"): str,
                vol.Required("preset"): str,
                vol.Optional("category"): str,
                vol.Optional("gain"): vol.Coerce(float),
                vol.Optional("loop"): bool,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_STREAM,
        lambda call: _async_play_stream(hass, client, call),
        schema=vol.Schema(
            {
                vol.Required("camera"): str,
                vol.Required("url"): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_URL,
        lambda call: _async_play_url(hass, client, call),
        schema=vol.Schema(
            {
                vol.Required("camera"): str,
                vol.Required("url"): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_BROADCAST,
        lambda call: _async_broadcast(hass, client, call),
        schema=vol.Schema(
            {
                vol.Optional("text"): str,
                vol.Optional("preset"): str,
                vol.Optional("voice"): str,
                vol.Optional("gain"): vol.Coerce(float),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_BEEP,
        lambda call: _async_beep(hass, client, call),
        schema=vol.Schema({vol.Required("camera"): str}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP,
        lambda call: _async_stop(hass, client, call),
        schema=vol.Schema({vol.Optional("camera"): str}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PAUSE,
        lambda call: _async_pause(hass, client, call),
        schema=vol.Schema({vol.Optional("camera"): str}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESUME,
        lambda call: _async_resume(hass, client, call),
        schema=vol.Schema({vol.Optional("camera"): str}),
    )


async def _async_speak(hass, client, call):
    await client.speak(
        camera=call.data["camera"],
        text=call.data["text"],
        voice=call.data.get("voice", ""),
        gain=call.data.get("gain", 0),
    )


async def _async_play_preset(hass, client, call):
    await client.play_preset(
        camera=call.data["camera"],
        preset=call.data["preset"],
        category=call.data.get("category", ""),
        gain=call.data.get("gain", 0),
        loop=call.data.get("loop", False),
    )


async def _async_play_stream(hass, client, call):
    await client.play_stream(camera=call.data["camera"], url=call.data["url"])


async def _async_play_url(hass, client, call):
    await client.play_url(camera=call.data["camera"], url=call.data["url"])


async def _async_broadcast(hass, client, call):
    await client.broadcast(
        text=call.data.get("text", ""),
        preset=call.data.get("preset", ""),
        voice=call.data.get("voice", ""),
        gain=call.data.get("gain", 0),
    )


async def _async_beep(hass, client, call):
    await client.beep(camera=call.data["camera"])


async def _async_stop(hass, client, call):
    await client.stop(camera=call.data.get("camera", ""))


async def _async_pause(hass, client, call):
    await client.pause(camera=call.data.get("camera", ""))


async def _async_resume(hass, client, call):
    await client.resume(camera=call.data.get("camera", ""))
