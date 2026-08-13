"""The camspeak Home Assistant integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import CamspeakApiClient
from .const import CONF_URL, CONF_VERIFY_SSL, DOMAIN, LOGGER
from .coordinator import CamspeakCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
]

type CamspeakConfigEntry = ConfigEntry[CamspeakCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CamspeakConfigEntry) -> bool:
    """Set up camspeak from a config entry."""
    base_url = entry.data[CONF_URL]
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)

    client = CamspeakApiClient(
        base_url,
        session=async_get_clientsession(hass, verify_ssl=verify_ssl),
    )

    coordinator = CamspeakCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await _async_register_services(hass, coordinator)
    await coordinator.async_start_sse_listener()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: CamspeakConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = entry.runtime_data
    await coordinator.async_stop_sse_listener()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Only remove services if no other camspeak entries are loaded
        other_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id
        ]
        if not other_entries:
            _async_remove_services(hass)
    return unload_ok


async def _async_register_services(hass: HomeAssistant, coordinator: CamspeakCoordinator) -> None:
    """Register camspeak services."""
    client = coordinator.client

    async def _async_speak(call: ServiceCall) -> None:
        """Speak text on a camera."""
        await client.speak(
            camera=call.data["camera"],
            text=call.data["text"],
            voice=call.data.get("voice", ""),
            gain=call.data.get("gain", 0),
        )

    async def _async_play_preset(call: ServiceCall) -> None:
        """Play a preset on a camera."""
        await client.play_preset(
            camera=call.data["camera"],
            preset=call.data["preset"],
            category=call.data.get("category", ""),
            gain=call.data.get("gain", 0),
            loop=call.data.get("loop", False),
        )

    async def _async_play_stream(call: ServiceCall) -> None:
        """Stream a live URL to a camera."""
        await client.play_stream(camera=call.data["camera"], url=call.data["url"])

    async def _async_play_url(call: ServiceCall) -> None:
        """Download and play a URL on a camera."""
        await client.play_url(camera=call.data["camera"], url=call.data["url"])

    async def _async_broadcast(call: ServiceCall) -> None:
        """Broadcast to all cameras."""
        await client.broadcast(
            text=call.data.get("text", ""),
            preset=call.data.get("preset", ""),
            voice=call.data.get("voice", ""),
            gain=call.data.get("gain", 0),
        )

    async def _async_beep(call: ServiceCall) -> None:
        """Play a test beep."""
        await client.beep(camera=call.data["camera"])

    async def _async_stop(call: ServiceCall) -> None:
        """Stop playback."""
        await client.stop(camera=call.data.get("camera", ""))

    async def _async_pause(call: ServiceCall) -> None:
        """Pause playback."""
        await client.pause(camera=call.data.get("camera", ""))

    async def _async_resume(call: ServiceCall) -> None:
        """Resume playback."""
        await client.resume(camera=call.data.get("camera", ""))

    hass.services.async_register(
        DOMAIN,
        "speak",
        _async_speak,
        schema=vol.Schema(
            {
                vol.Required("camera"): cv.string,
                vol.Required("text"): cv.string,
                vol.Optional("voice"): cv.string,
                vol.Optional("gain"): vol.Coerce(float),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "play_preset",
        _async_play_preset,
        schema=vol.Schema(
            {
                vol.Required("camera"): cv.string,
                vol.Required("preset"): cv.string,
                vol.Optional("category"): cv.string,
                vol.Optional("gain"): vol.Coerce(float),
                vol.Optional("loop"): bool,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "play_stream",
        _async_play_stream,
        schema=vol.Schema(
            {
                vol.Required("camera"): cv.string,
                vol.Required("url"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "play_url",
        _async_play_url,
        schema=vol.Schema(
            {
                vol.Required("camera"): cv.string,
                vol.Required("url"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "broadcast",
        _async_broadcast,
        schema=vol.Schema(
            {
                vol.Optional("text"): cv.string,
                vol.Optional("preset"): cv.string,
                vol.Optional("voice"): cv.string,
                vol.Optional("gain"): vol.Coerce(float),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "beep",
        _async_beep,
        schema=vol.Schema(
            {
                vol.Required("camera"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "stop",
        _async_stop,
        schema=vol.Schema(
            {
                vol.Optional("camera"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "pause",
        _async_pause,
        schema=vol.Schema(
            {
                vol.Optional("camera"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "resume",
        _async_resume,
        schema=vol.Schema(
            {
                vol.Optional("camera"): cv.string,
            }
        ),
    )


@callback
def _async_remove_services(hass: HomeAssistant) -> None:
    """Remove camspeak services."""
    for service in (
        "speak",
        "play_preset",
        "play_stream",
        "play_url",
        "broadcast",
        "beep",
        "stop",
        "pause",
        "resume",
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


async def async_migrate_entry(hass: HomeAssistant, entry: CamspeakConfigEntry) -> bool:
    """Migrate old entry."""
    LOGGER.debug("Migrating configuration from version %s", entry.version)
    return True
