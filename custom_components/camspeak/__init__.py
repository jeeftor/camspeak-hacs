"""The camspeak Home Assistant integration."""

from collections.abc import Awaitable, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    service as service_helpers,
    target as target_helpers,
)
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
        other_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id
        ]
        if not other_entries:
            _async_remove_services(hass)
    return unload_ok


def _resolve_camera_name(hass: HomeAssistant, entity_id: str) -> str:
    """Resolve media_player entity_id to camspeak camera name via device registry."""
    registry = er.async_get(hass)
    entity_entry = registry.async_get(entity_id)
    if entity_entry is None or entity_entry.device_id is None:
        raise HomeAssistantError(f"Camera not found for entity {entity_id}")

    dev_registry = dr.async_get(hass)
    device = dev_registry.async_get(entity_entry.device_id)
    if device is None:
        raise HomeAssistantError(f"Device not found for entity {entity_id}")

    for domain, ident in device.identifiers:
        if domain == DOMAIN:
            return ident

    raise HomeAssistantError(f"Camera name not found for entity {entity_id}")


async def _async_resolve_cameras(hass: HomeAssistant, call: ServiceCall) -> list[str]:
    """Resolve service call targets to camera names."""
    target_selection = target_helpers.TargetSelection(call.data)
    referenced = target_helpers.async_extract_referenced_entity_ids(
        hass, target_selection, expand_group=True
    )
    if not referenced.referenced:
        return []
    return [_resolve_camera_name(hass, eid) for eid in referenced.referenced]


def _make_per_camera_handler(
    hass: HomeAssistant,
    api_call: Callable[..., Awaitable],
) -> Callable[[ServiceCall], Awaitable[None]]:
    """Create a service handler that resolves targets and calls the API per camera."""

    async def handler(call: ServiceCall) -> None:
        cameras = await _async_resolve_cameras(hass, call)
        data = service_helpers.remove_entity_service_fields(call)
        for camera in cameras:
            await api_call(camera=camera, **data)

    return handler


def _make_all_or_camera_handler(
    hass: HomeAssistant,
    api_call: Callable[..., Awaitable],
) -> Callable[[ServiceCall], Awaitable[None]]:
    """Create a handler that calls API per camera, or all if no target."""

    async def handler(call: ServiceCall) -> None:
        cameras = await _async_resolve_cameras(hass, call)
        if cameras:
            for camera in cameras:
                await api_call(camera=camera)
        else:
            await api_call(camera="")

    return handler


async def _async_register_services(hass: HomeAssistant, coordinator: CamspeakCoordinator) -> None:
    """Register camspeak services."""
    client = coordinator.client

    async def _async_broadcast(call: ServiceCall) -> None:
        await client.broadcast(
            text=call.data.get("text", ""),
            preset=call.data.get("preset", ""),
            voice=call.data.get("voice", ""),
            gain=call.data.get("gain", 0),
        )

    services: dict[str, tuple[Callable, vol.Schema]] = {
        "speak": (
            _make_per_camera_handler(hass, client.speak),
            vol.Schema(
                {
                    **cv.ENTITY_SERVICE_FIELDS,
                    vol.Required("text"): cv.string,
                    vol.Optional("voice"): cv.string,
                    vol.Optional("gain"): vol.Coerce(float),
                }
            ),
        ),
        "play_preset": (
            _make_per_camera_handler(hass, client.play_preset),
            vol.Schema(
                {
                    **cv.ENTITY_SERVICE_FIELDS,
                    vol.Required("preset"): cv.string,
                    vol.Optional("category"): cv.string,
                    vol.Optional("gain"): vol.Coerce(float),
                    vol.Optional("loop"): bool,
                }
            ),
        ),
        "play_stream": (
            _make_per_camera_handler(hass, client.play_stream),
            vol.Schema(
                {
                    **cv.ENTITY_SERVICE_FIELDS,
                    vol.Required("url"): cv.string,
                }
            ),
        ),
        "play_url": (
            _make_per_camera_handler(hass, client.play_url),
            vol.Schema(
                {
                    **cv.ENTITY_SERVICE_FIELDS,
                    vol.Required("url"): cv.string,
                }
            ),
        ),
        "broadcast": (
            _async_broadcast,
            vol.Schema(
                {
                    vol.Optional("text"): cv.string,
                    vol.Optional("preset"): cv.string,
                    vol.Optional("voice"): cv.string,
                    vol.Optional("gain"): vol.Coerce(float),
                }
            ),
        ),
        "beep": (
            _make_per_camera_handler(hass, client.beep),
            vol.Schema({**cv.ENTITY_SERVICE_FIELDS}),
        ),
        "stop": (
            _make_all_or_camera_handler(hass, client.stop),
            vol.Schema({**cv.ENTITY_SERVICE_FIELDS}),
        ),
        "pause": (
            _make_all_or_camera_handler(hass, client.pause),
            vol.Schema({**cv.ENTITY_SERVICE_FIELDS}),
        ),
        "resume": (
            _make_all_or_camera_handler(hass, client.resume),
            vol.Schema({**cv.ENTITY_SERVICE_FIELDS}),
        ),
    }

    for name, (handler, schema) in services.items():
        hass.services.async_register(DOMAIN, name, handler, schema=schema)


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
