"""Binary sensor platform for camspeak cameras."""

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CamspeakCoordinator
from .entity import CamspeakEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[CamspeakCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up camspeak binary sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(CamspeakOnlineSensor(coordinator, name) for name in coordinator.data.cameras)


class CamspeakOnlineSensor(CamspeakEntity, BinarySensorEntity):
    """Binary sensor showing whether a camera is online."""

    _attr_icon = "mdi:camera"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CamspeakCoordinator, camera_name: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, camera_name)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{camera_name}_online"
        self._attr_name = "online"

    @override
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._update_state()

    def _update_state(self) -> None:
        """Update entity state from coordinator data."""
        data = self.coordinator.data
        if not data or self._camera_name not in data.cameras:
            self._attr_is_on = False
        else:
            cam = data.cameras[self._camera_name].camera
            self._attr_is_on = cam.get("online", False)

    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        self._update_state()
        self.async_write_ha_state()
