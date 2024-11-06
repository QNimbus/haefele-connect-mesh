"""DataUpdateCoordinator for Häfele Connect Mesh."""

from __future__ import annotations

import logging
import asyncio
from datetime import timedelta, datetime
from typing import Dict, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers import device_registry as dr

from .api.client import HafeleClient
from .const import DOMAIN
from .models.device import Device

_LOGGER = logging.getLogger(__name__)

# Check device details every 5 minutes
DEVICE_DETAILS_UPDATE_INTERVAL = timedelta(minutes=5)


class HafeleUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, client: HafeleClient, device: Device
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{device.name}",
            update_interval=timedelta(seconds=30),
            always_update=False,
        )
        self.client = client
        self.device = device
        self._device_registry = dr.async_get(hass)
        self._last_device_check = datetime.min
        self._device_check_task: asyncio.Task | None = None

    async def _check_device_details(self) -> None:
        """Check for device detail updates in a separate task."""
        try:
            # Use Home Assistant's timeout context manager
            async with self.hass.timeout.async_timeout(30):  # 30 second timeout
                updated_device = await self.client.get_device_details(self.device.id)

                # If device name has changed, update the device registry
                if updated_device.name != self.device.name:
                    _LOGGER.debug(
                        "Device name changed from '%s' to '%s'",
                        self.device.name,
                        updated_device.name,
                    )

                    # Update device registry
                    device_entry = self._device_registry.async_get_device(
                        identifiers={(DOMAIN, self.device.id)}
                    )
                    if device_entry:
                        self._device_registry.async_update_device(
                            device_entry.id, name=updated_device.name
                        )

                    # Update local device reference
                    self.device = updated_device
                    # Update coordinator name
                    self.name = updated_device.name

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout checking device details for %s", self.device.name)
        except Exception as error:
            _LOGGER.error(
                "Error checking device details for %s: %s", self.device.name, str(error)
            )
        finally:
            self._device_check_task = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            _LOGGER.debug(
                "Fetching status for device %s (ID: %s)",
                self.device.name,
                self.device.id,
            )
            status = await self.client.get_device_status(self.device.id)

            # Check if it's time to update device details and no check is currently running
            now = datetime.now()
            if (
                now - self._last_device_check > DEVICE_DETAILS_UPDATE_INTERVAL
                and self._device_check_task is None
            ):
                self._last_device_check = now
                # Use Home Assistant's task creation method instead of asyncio directly
                self._device_check_task = self.hass.async_create_task(
                    self._check_device_details()
                )

            self.device.update_timestamp()

            transformed_data = {
                "state": {
                    k: status["state"][k]
                    for k in ["power", "lightness", "lastLightness"]
                }
            }

            _LOGGER.debug(
                "Processed status for device %s: %s", self.device.name, transformed_data
            )
            return transformed_data

        except Exception as error:
            self.device.update_timestamp()
            _LOGGER.error("Error updating device %s: %s", self.device.name, str(error))
            raise UpdateFailed(f"Error communicating with API: {error}")
