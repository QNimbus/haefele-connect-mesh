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

    # Log available devices and their types
    _LOGGER.debug(
        "Setting up switches. Available devices: %s",
        [(d.id, d.type, d.is_socket) for d in devices]
    )

    entities = []
    for device in devices:
        if device.id in coordinators and device.is_socket:
            try:
                coordinator = coordinators[device.id]
                _LOGGER.debug(
                    "Creating switch entity for device %s (coordinator data: %s)",
                    device.id,
                    coordinator.data
                )
                
                entities.append(
                    HaefeleConnectMeshSwitch(coordinator, device, config_entry.entry_id)
                )
            except Exception as err:
                _LOGGER.error(
                    "Error creating switch entity for device %s: %s",
                    device.id,
                    str(err)
                )
                continue

    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug(
            "No switch entities created. Devices: %s, Coordinators: %s",
            devices,
            coordinators.keys()
        )


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
        try:
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
        except Exception as err:
            _LOGGER.error("Error checking availability for %s: %s", self.name, str(err))
            return False

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

        # Try to get initial state
        try:
            status = await self.coordinator.client.get_device_status(self._device.id)
            self.coordinator.data = {"state": status}
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.warning(
                "Could not get initial state for %s: %s",
                self._device.id,
                str(err)
            )
            
            # Restore state if we don't have fresh data
            if last_state := await self.async_get_last_state():
                self._attr_is_on = last_state.state == "on"
  