"""Platform for Häfele Connect Mesh light integration."""

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, UTC
import json
import math

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util.color import (
    value_to_brightness,
    brightness_to_value,
    color_temperature_kelvin_to_mired,
    color_temperature_mired_to_kelvin,
)
from homeassistant.util.percentage import percentage_to_ranged_value

from .const import (
    DOMAIN,
    NAME,
    BRIGHTNESS_SCALE_PERCENTAGE,
    BRIGHTNESS_SCALE_MESH,
    BRIGHTNESS_SCALE_HA,
    MIN_KELVIN,
    MAX_KELVIN,
    MIN_MIREDS,
    MAX_MIREDS,
)
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
        groups = await client.get_groups_for_network(network_id)
        lights = [device for device in devices if device.is_light] + [
            group for group in groups if group.is_light
        ]

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

        # Set color modes based on device capabilities
        if device.supports_hsl:
            self._attr_color_mode = ColorMode.HS
            self._attr_supported_color_modes = {ColorMode.HS}
        elif device.supports_color_temp:
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_min_mireds = MIN_MIREDS  # Adjust if needed
            self._attr_max_mireds = MAX_MIREDS  # Adjust if needed
        else:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

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
            return value_to_brightness(BRIGHTNESS_SCALE_MESH, lightness)
        return None

    @property
    def color_temp(self) -> int | None:
        """Return the color temperature in mireds."""
        if not self.available or not self.is_on or not self._device.supports_color_temp:
            return None

        temperature = self.coordinator.data["state"].get("temperature")
        if temperature is not None:
            # Convert mesh value to Kelvin first
            kelvin = MIN_KELVIN + (temperature / 65535) * (MAX_KELVIN - MIN_KELVIN)
            return color_temperature_kelvin_to_mired(kelvin)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        try:
            new_state = {
                "power": True,
                "lightness": self.coordinator.data["state"]["lightness"],
            }

            if ATTR_BRIGHTNESS in kwargs:
                try:
                    lightness = brightness_to_value(
                        BRIGHTNESS_SCALE_PERCENTAGE, kwargs[ATTR_BRIGHTNESS]
                    )
                except ValueError as ex:
                    raise ServiceValidationError(
                        f"Invalid brightness value for {self.name}: {ex}"
                    ) from ex

                try:
                    await self.coordinator.client.set_lightness(
                        self._device, lightness / 100
                    )
                    new_state["lightness"] = percentage_to_ranged_value(
                        BRIGHTNESS_SCALE_MESH, lightness
                    )
                except HafeleAPIError as ex:
                    raise HomeAssistantError(
                        f"Failed to set brightness for {self.name}: {ex}"
                    ) from ex

            if ATTR_COLOR_TEMP in kwargs and self._device.supports_color_temp:
                mireds = kwargs[ATTR_COLOR_TEMP]
                try:
                    # Convert mireds to Kelvin, then to mesh value
                    kelvin = color_temperature_mired_to_kelvin(mireds)
                    # Map Kelvin range to mesh range (0-65535)
                    mesh_temp = round(
                        ((kelvin - MIN_KELVIN) / (MAX_KELVIN - MIN_KELVIN)) * 65535
                    )

                    await self.coordinator.client.set_temperature(
                        self._device, mesh_temp
                    )
                    new_state["temperature"] = kwargs[ATTR_COLOR_TEMP]
                except ValueError as ex:
                    raise ServiceValidationError(
                        f"Invalid color temperature value for {self.name}: {ex}"
                    ) from ex
                except HafeleAPIError as ex:
                    raise HomeAssistantError(
                        f"Failed to set color temperature for {self.name}: {ex}"
                    ) from ex

            if ATTR_HS_COLOR in kwargs and self._device.supports_hsl:
                try:
                    hue, saturation = kwargs[ATTR_HS_COLOR]
                    await self.coordinator.client.set_hsl(self._device, hue, saturation)
                    new_state["hue"] = hue
                    new_state["saturation"] = saturation
                except ValueError as ex:
                    raise ServiceValidationError(
                        f"Invalid HS color values for {self.name}: {ex}"
                    ) from ex
                except HafeleAPIError as ex:
                    raise HomeAssistantError(
                        f"Failed to set HS color for {self.name}: {ex}"
                    ) from ex

            try:
                await self.coordinator.client.power_on(self._device)
            except HafeleAPIError as ex:
                raise HomeAssistantError(
                    f"Failed to power on {self.name}: {ex}"
                ) from ex

            # Update coordinator data immediately
            self.coordinator.data = {"state": new_state}
            self.async_write_ha_state()

        except (ServiceValidationError, HomeAssistantError):
            # Re-raise these as they are already properly handled exceptions
            raise
        except Exception as ex:
            # Catch any other unexpected exceptions and wrap them
            _LOGGER.exception("Unexpected error turning on %s", self.name)
            raise HomeAssistantError(f"Unexpected error turning on {self.name}") from ex

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
        # Get network info from the device
        network_info = {}
        try:
            # Get network data from the config entry
            network_id = self._device.network_id
            entry = self.platform.config_entry

            if entry and entry.data.get("network_id") == network_id:
                network_info = {
                    "network_id": network_id,
                    "network_name": entry.title,  # Config entry title is the network name
                }
        except Exception as ex:
            _LOGGER.debug("Could not get network info: %s", str(ex))

        return {
            **network_info,
            "device_id": self._device.id,
            "device_type": self._device.type,
            "last_update": self._device.last_updated.isoformat(),
            "last_update_success": self.coordinator.last_update_success,
            "update_interval": self.coordinator.update_interval.total_seconds(),
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
