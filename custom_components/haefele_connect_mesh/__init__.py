"""The Häfele Connect Mesh integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from .api.client import HafeleClient
from .coordinator import HafeleUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "haefele_connect_mesh"
PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

PARALLEL_UPDATES = 0


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Häfele Connect Mesh component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Häfele Connect Mesh from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    session = async_get_clientsession(hass)
    client = HafeleClient(entry.data["api_token"], session, timeout=10)

    # Get network ID from config entry
    network_id = entry.data["network_id"]

    try:
        # Get gateways for this network
        gateways = await client.get_gateways()
        network_gateways = [g for g in gateways if g.network_id == network_id]

        # Register gateways as devices
        device_registry = dr.async_get(hass)

        for gateway in network_gateways:
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, gateway.id)},
                name=f"Häfele Gateway {gateway.id[:8]}",
                manufacturer="Häfele",
                model="Connect Mesh Gateway",
                sw_version=gateway.firmware,
                entry_type=dr.DeviceEntryType.SERVICE,
            )

        # Store client and gateways for use by platforms
        hass.data[DOMAIN][entry.entry_id] = {
            "client": client,
            "gateways": network_gateways,
            "coordinators": {},
            "network_id": network_id,
            "devices": [],
        }

        # Fetch initial data and create coordinators
        devices = await client.get_devices_for_network(network_id)
        for device in devices:
            coordinator = HafeleUpdateCoordinator(hass, client, device)
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][entry.entry_id]["coordinators"][device.id] = coordinator
            hass.data[DOMAIN][entry.entry_id]["devices"].append(device)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as error:
        _LOGGER.error("Failed to set up Häfele Connect Mesh: %s", str(error))
        raise ConfigEntryNotReady from error
    else:
        return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a device from the integration.
    
    This function is called when a user initiates device deletion from the UI.
    We need to:
    1. Find the device in our data structure
    2. Remove it from any coordinators
    3. Clean up any device-specific data
    """
    try:
        # Get the device ID from the device entry identifiers
        device_id = None
        for identifier in device_entry.identifiers:
            if identifier[0] == DOMAIN:
                device_id = identifier[1]
                break
                
        if not device_id:
            return False

        # Get our integration data
        client = hass.data[DOMAIN][config_entry.entry_id]["client"]
        coordinators = hass.data[DOMAIN][config_entry.entry_id]["coordinators"]
        devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]

        # Remove the coordinator for this device if it exists
        if device_id in coordinators:
            coordinator = coordinators.pop(device_id)
            # Cancel any pending updates
            coordinator.async_shutdown()

        # Remove the device from our devices list
        devices[:] = [d for d in devices if d.id != device_id]

        _LOGGER.info("Successfully removed device %s", device_id)
        return True

    except Exception as ex:
        _LOGGER.error("Error removing device %s: %s", device_entry.id, str(ex))
        return False
