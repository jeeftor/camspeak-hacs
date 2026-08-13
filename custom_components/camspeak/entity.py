"""Base entity for camspeak."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CamspeakCoordinator

_MANUFACTURERS = {
    "hikvision": "Hikvision",
    "reolink": "Reolink",
    "go2rtc": "go2rtc",
    "onvif": "ONVIF",
}


class CamspeakEntity(CoordinatorEntity[CamspeakCoordinator], Entity):
    """Base entity for camspeak cameras."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CamspeakCoordinator,
        camera_name: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._camera_name = camera_name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{camera_name}"

        cam_data = coordinator.data.cameras.get(camera_name)
        cam = cam_data.camera if cam_data else {}
        cam_type = cam.get("type", "")
        manufacturer = _MANUFACTURERS.get(cam_type, "IP Camera")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, camera_name)},
            name=camera_name,
            manufacturer=manufacturer,
            model=cam_type.capitalize() if cam_type else None,
            configuration_url=f"http://{cam['ip']}" if cam.get("ip") else None,
        )
