"""Platform for Häfele Connect Mesh binary sensor integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
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
    """Set up the Häfele Connect Mesh Binary Sensor platform."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id]["coordinators"]
    devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]

    entities = []
    for device in devices:
        coordinator = coordinators[device.id]
        entities.append(
            HaefeleUpdateSuccessSensor(coordinator, device, config_entry.entry_id)
        )

    async_add_entities(entities)


class HaefeleUpdateSuccessSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for tracking update success of Häfele devices."""

    def __init__(
        self,
        coordinator: HafeleUpdateCoordinator,
        device: Device,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self._device = device
        self._entry_id = entry_id
        self._attr_translation_key = "last_update_success"
        self._attr_unique_id = f"{device.id}_last_update_success"
        self._attr_has_entity_name = True
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        return super()._handle_coordinator_update()

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
            manufacturer="Häfele",
            model=self._device.type.value.split(".")[-1].capitalize(),
            sw_version=self._device.bootloader_version,
            via_device=(DOMAIN, gateway_id) if gateway_id else None,
        )

    @property
    def is_on(self) -> bool:
        """Return True if the last update was successful."""
        return self.coordinator.last_update_success

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Always return True since this entity reflects the update status itself
        return True
