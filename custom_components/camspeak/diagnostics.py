"""Diagnostics support for camspeak."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_URL, CONF_VERIFY_SSL
from .coordinator import CamspeakCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[CamspeakCoordinator]
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    if data is None:
        return {"entry": entry.as_dict(), "cameras": {}}

    return {
        "entry": {
            "title": entry.title,
            "url": entry.data.get(CONF_URL),
            "verify_ssl": entry.data.get(CONF_VERIFY_SSL),
        },
        "cameras": {
            name: {
                "online": cam_data.camera.get("online"),
                "type": cam_data.camera.get("type"),
                "playback": cam_data.playback,
                "preset_count": len(cam_data.presets),
            }
            for name, cam_data in data.cameras.items()
        },
    }
