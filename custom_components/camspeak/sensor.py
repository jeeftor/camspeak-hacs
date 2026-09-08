"""Sensor platform for camspeak cameras."""

from typing import override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: list[str] = [PLAYBACK_IDLE, PLAYBACK_PLAYING, PLAYBACK_PAUSED]  # noqa: RUF012

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{camera_name}_playback"
        self._attr_name = "playback"

    @override
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._update_state()

    def _update_state(self) -> None:
        """Update entity state from coordinator data."""
        if not self.coordinator.last_update_success:
            self._attr_available = False
            return
        self._attr_available = True
        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            self._attr_native_value = PLAYBACK_IDLE
            self._attr_extra_state_attributes = {}
        else:
            playback = data.cameras[self._camera_name].playback
            self._attr_native_value = playback.get("state", PLAYBACK_IDLE)
            attrs = {
                "source": playback.get("source", ""),
                "detail": playback.get("detail", ""),
                "started_at": playback.get("started_at", ""),
                "paused_at": playback.get("paused_at", ""),
            }
            # Prefer live SSE level (real-time), fall back to polled level
            level = self.coordinator.live_levels.get(self._camera_name)
            if level is None:
                level = playback.get("level")
            if level is not None:
                attrs["audio_level"] = round(level, 3)
            self._attr_extra_state_attributes = attrs

    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        self._update_state()
        self.async_write_ha_state()
