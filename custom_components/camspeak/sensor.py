"""Sensor platform for camspeak cameras."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PLAYBACK_IDLE, PLAYBACK_PAUSED, PLAYBACK_PLAYING
from .coordinator import CamspeakCoordinator
from .entity import CamspeakEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[CamspeakCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up camspeak sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        CamspeakPlaybackSensor(coordinator, name) for name in coordinator.data.cameras
    )


class CamspeakSensor(CamspeakEntity, SensorEntity):
    """Base class for camspeak sensors."""

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, camera_name)


class CamspeakPlaybackSensor(CamspeakSensor):
    """Sensor showing the current playback state of a camera."""

    _attr_icon = "mdi:speaker-message"
    _attr_options: list[str] = [PLAYBACK_IDLE, PLAYBACK_PLAYING, PLAYBACK_PAUSED]  # noqa: RUF012

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{camera_name}_playback"
        self._attr_name = "playback"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            self._attr_native_value = PLAYBACK_IDLE
            self._attr_extra_state_attributes = {}
        else:
            playback = data.cameras[self._camera_name].playback
            self._attr_native_value = playback.get("state", PLAYBACK_IDLE)
            self._attr_extra_state_attributes = {
                "source": playback.get("source", ""),
                "detail": playback.get("detail", ""),
                "started": playback.get("started", ""),
                "paused_at": playback.get("paused_at", ""),
            }
        self.async_write_ha_state()
