"""DataUpdateCoordinator for Häfele Connect Mesh."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api.client import HafeleClient
from .const import DOMAIN
from .models.device import Device

_LOGGER = logging.getLogger(__name__)


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
        )
        self.client = client
        self.device = device

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            _LOGGER.debug(
                "Fetching status for device %s (ID: %s)",
                self.device.name,
                self.device.id,
            )
            status = await self.client.get_device_status(self.device.id)
            self.device.update_timestamp()

            # Transform the data to match our expected structure
            transformed_data = {
                "state": {
                    "power": status["state"]["power"],
                    "lightness": status["state"]["lightness"],
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
