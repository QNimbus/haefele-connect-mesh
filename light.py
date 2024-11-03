"""Platform for Häfele Connect Mesh light integration."""

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, UTC
import json

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, NAME
from .api.client import HafeleClient, HafeleAPIError
from .coordinator import HafeleUpdateCoordinator
from .models.device import Device as HafeleDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Häfele Connect Mesh Light platform."""
    client: HafeleClient = hass.data[DOMAIN][config_entry.entry_id]["client"]
    network_id = config_entry.data["network_id"]

    try:
        devices = await client.get_devices_for_network(network_id)
        lights = [device for device in devices if device.is_light]

        # Create coordinators for each device
        coordinators = {}
        for light in lights:
            coordinator = HafeleUpdateCoordinator(hass, client, light)
            await coordinator.async_config_entry_first_refresh()
            coordinators[light.id] = coordinator

        # Create light entities
        entities = [
            HaefeleConnectMeshLight(
                coordinators[light.id], light, config_entry.entry_id
            )
            for light in lights
        ]
        async_add_entities(entities)

    except Exception as ex:
        _LOGGER.error("Error setting up Häfele lights: %s", str(ex))


class HaefeleConnectMeshLight(CoordinatorEntity, LightEntity, RestoreEntity):
    """Representation of a Häfele Connect Mesh Light."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_name = None

    def __init__(
        self,
        coordinator: HafeleUpdateCoordinator,
        device: HafeleDevice,
        entry_id: str,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)

        self._device = device
        self._entry_id = entry_id
        self._attr_unique_id = f"{device.id}_light"
        self._attr_name = "Light"

        # Device info for device registry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="Häfele",
            model=device.type.split(".")[-1].capitalize(),  # Extract model type
            sw_version=device.bootloader_version,
            via_device=(DOMAIN, entry_id),  # Connect to the network controller
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(
            "Coordinator update for %s: Raw Data=%s, Is On=%s, Brightness=%s",
            self.name,
            self.coordinator.data,
            self.is_on,
            self.brightness,
        )
        super()._handle_coordinator_update()

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
            and "lightness" in self.coordinator.data["state"]
            # Check if last update was within reasonable time (2 minutes)
            and (datetime.now(UTC) - self._device.last_updated).total_seconds() < 120
        )

        _LOGGER.debug(
            "Availability check for %s: %s (Data: %s, Last Update: %s)",
            self.name,
            is_available,
            self.coordinator.data,
            self._device.last_updated,
        )
        return is_available

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        if not self.available:
            return None
        # Debug log to see what data we're working with
        _LOGGER.debug(
            "Checking is_on for %s with data: %s", self.name, self.coordinator.data
        )
        return self.coordinator.data["state"]["power"]  # API returns boolean

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if not self.available or not self.is_on:
            return None

        lightness = self.coordinator.data["state"].get("lightness")
        if lightness is not None:
            # Use the client's static method for consistent conversion
            return self.coordinator.client.mesh_to_brightness(lightness)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        try:
            new_state = {
                "power": True,
                "lightness": self.coordinator.data["state"]["lightness"],
            }

            if ATTR_BRIGHTNESS in kwargs:
                brightness = kwargs[ATTR_BRIGHTNESS]
                lightness = self.coordinator.client.brightness_to_api(brightness)
                try:
                    await self.coordinator.client.set_lightness(self._device, lightness)
                    new_state["lightness"] = self.coordinator.client.brightness_to_mesh(
                        brightness
                    )
                except HafeleAPIError as ex:
                    _LOGGER.error(
                        "Failed to set brightness for light %s to %s: %s",
                        self.name,
                        brightness,
                        str(ex),
                    )
                    raise

            try:
                await self.coordinator.client.power_on(self._device)
            except HafeleAPIError as ex:
                _LOGGER.error(
                    "Failed to power on light %s: %s",
                    self.name,
                    str(ex),
                )
                raise

            # Update coordinator data immediately
            self.coordinator.data = {"state": new_state}
            self.async_write_ha_state()

        except HafeleAPIError as ex:
            _LOGGER.error(
                "Failed to turn on light %s: %s",
                self.name,
                str(ex),
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            await self.coordinator.client.power_off(self._device)

            # Update coordinator data immediately
            self.coordinator.data = {
                "state": {
                    "power": False,
                    "lightness": self.coordinator.data["state"]["lightness"],
                }
            }
            self.async_write_ha_state()

            # Then refresh from API to confirm
            # await self.coordinator.async_request_refresh()

        except HafeleAPIError as ex:
            _LOGGER.error("Failed to turn off light %s: %s", self.name, str(ex))

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "device_id": self._device.id,
            "last_update": self._device.last_updated.isoformat(),
            "last_update_success": self.coordinator.last_update_success,
            "update_interval": self.coordinator.update_interval.total_seconds(),
            "device_type": self._device.type,
            "bootloader_version": self._device.bootloader_version,
            "raw_state": self.coordinator.data["state"]
            if self.coordinator.data
            else None,
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Only restore state if we don't have fresh data yet
        if self.coordinator.data is None:
            if last_state := await self.async_get_last_state():
                # Only restore the state, don't update coordinator data
                if last_state.state == "on":
                    self._attr_is_on = True
                    self._attr_brightness = last_state.attributes.get("brightness", 255)
                else:
                    self._attr_is_on = False
                    self._attr_brightness = 0

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        raise NotImplementedError(
            "Please use the async_turn_on method instead. This entity only supports async operation."
        )

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        raise NotImplementedError(
            "Please use the async_turn_off method instead. This entity only supports async operation."
        )
