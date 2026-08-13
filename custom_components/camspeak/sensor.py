"""Sensor platform for camspeak cameras."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PLAYBACK_IDLE, PLAYBACK_PAUSED, PLAYBACK_PLAYING
from .coordinator import CamspeakCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camspeak sensors from a config entry."""
    coordinator: CamspeakCoordinator = entry.runtime_data
    cameras = coordinator.data or {}
    entities: list[CamspeakSensor] = []
    for name in cameras:
        entities.append(CamspeakPlaybackSensor(coordinator, name))
        entities.append(CamspeakOnlineSensor(coordinator, name))
    async_add_entities(entities, update_before_add=True)


class CamspeakSensor(CoordinatorEntity[CamspeakCoordinator], SensorEntity):
    """Base class for camspeak sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._camera_name = camera_name
        cam = coordinator.data[camera_name]["camera"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, camera_name)},
            "name": camera_name,
            "manufacturer": cam.get("type", "IP Camera"),
            "model": cam.get("type", ""),
        }


class CamspeakPlaybackSensor(CamspeakSensor):
    """Sensor showing the current playback state of a camera."""

    _attr_icon = "mdi:speaker-message"

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{camera_name}_playback"
        self._attr_name = "playback"
        self._attr_options = [PLAYBACK_IDLE, PLAYBACK_PLAYING, PLAYBACK_PAUSED]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data:
            self._attr_native_value = PLAYBACK_IDLE
            self._attr_extra_state_attributes = {}
        else:
            playback = data[self._camera_name]["playback"]
            self._attr_native_value = playback.get("state", PLAYBACK_IDLE)
            self._attr_extra_state_attributes = {
                "source": playback.get("source", ""),
                "detail": playback.get("detail", ""),
                "started": playback.get("started", ""),
                "paused_at": playback.get("paused_at", ""),
            }
        self.async_write_ha_state()


class CamspeakOnlineSensor(CamspeakSensor):
    """Binary sensor showing whether a camera is online."""

    _attr_icon = "mdi:camera"
    _attr_device_class = SensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{camera_name}_online"
        self._attr_name = "online"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data:
            self._attr_native_value = False
        else:
            cam = data[self._camera_name]["camera"]
            self._attr_native_value = cam.get("online", False)
        self.async_write_ha_state()
