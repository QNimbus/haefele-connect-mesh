"""Platform for Häfele Connect Mesh switch integration."""

from __future__ import annotations

import logging
from datetime import datetime, UTC

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import HafeleUpdateCoordinator
from .models.device import Device
from .exceptions import HafeleAPIError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Häfele Connect Mesh Switch platform."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id]["coordinators"]
    devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]

    # Create switch entities for socket devices
    entities = []
    for device in devices:
        if device.is_socket:
            coordinator = coordinators[device.id]
            entities.append(
                HaefeleConnectMeshSwitch(coordinator, device, config_entry.entry_id)
            )

    async_add_entities(entities)


class HaefeleConnectMeshSwitch(CoordinatorEntity, SwitchEntity, RestoreEntity):
    """Representation of a Häfele Connect Mesh Switch."""

    def __init__(
        self,
        coordinator: HafeleUpdateCoordinator,
        device: Device,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)

        self._device = device
        self._entry_id = entry_id
        self._attr_unique_id = f"{device.id}_switch"
        self._attr_name = device.name
        self._attr_has_entity_name = True

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
    def available(self) -> bool:
        """Return True if entity is available."""
        # First check coordinator's availability
        if not self.coordinator.last_update_success:
            return False

        # Then check data validity
        is_available = (
            self.coordinator.data is not None
            and isinstance(self.coordinator.data.get("state"), dict)
            and "power" in self.coordinator.data["state"]
            # Check if last update was within reasonable time (2 minutes)
            and (datetime.now(UTC) - self._device.last_updated).total_seconds() < 120
        )

        return is_available

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        if not self.available:
            return None
        return self.coordinator.data["state"]["power"]

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        try:
            await self.coordinator.client.power_on(self._device)
            self.coordinator.data = {"state": {"power": True}}
            self.async_write_ha_state()
        except HafeleAPIError as ex:
            raise HomeAssistantError(f"Failed to turn on {self.name}: {ex}") from ex

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        try:
            await self.coordinator.client.power_off(self._device)
            self.coordinator.data = {"state": {"power": False}}
            self.async_write_ha_state()
        except HafeleAPIError as ex:
            raise HomeAssistantError(f"Failed to turn off {self.name}: {ex}") from ex

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Restore state if we don't have fresh data
        if self.coordinator.data is None:
            if last_state := await self.async_get_last_state():
                self._attr_is_on = last_state.state == "on" 