"""Platform for Häfele Connect Mesh sensor integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .coordinator import HafeleUpdateCoordinator
from .models.device import Device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Häfele Connect Mesh Sensor platform."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id]["coordinators"]
    devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]

    # Only create entities for devices that have coordinators
    entities = []
    for device in devices:
        if device.id in coordinators:
            coordinator = coordinators[device.id]
            entities.append(
                HaefeleLastUpdateSensor(coordinator, device, config_entry.entry_id)
            )

    if entities:
        async_add_entities(entities)


class HaefeleLastUpdateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for tracking last update time of Häfele devices."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_update"
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: HafeleUpdateCoordinator,
        device: Device,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._device = device
        self._entry_id = entry_id
        self._attr_unique_id = f"{device.id}_last_update"
        self._attr_has_entity_name = True
        self._attr_translation_key = "last_update"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        # Get the gateway ID for this device's network
        gateway_id = None
        gateways = self.hass.data[DOMAIN][self._entry_id]["gateways"]
        if gateways:
            # Use the first gateway as the via_device
            gateway_id = gateways[0].id

        return DeviceInfo(
            identifiers={(DOMAIN, self._device.id)},
            name=self._device.name,
            manufacturer=self._device.type.manufacturer,
            model=self._device.type.value.split(".")[-1].capitalize(),
            sw_version=self._device.bootloader_version,
            via_device=(DOMAIN, gateway_id) if gateway_id else None,
        )

    @property
    def native_value(self) -> datetime:
        """Return the last update timestamp."""
        return self._device.last_updated
