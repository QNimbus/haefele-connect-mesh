"""Config flow for Häfele Connect Mesh integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_NETWORK_ID
from .api.client import HafeleClient
from .exceptions import HafeleAPIError

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Häfele Connect Mesh."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_token: str | None = None
        self._networks: list[dict] | None = None

    async def _validate_api_token(self, api_token: str) -> tuple[bool, str | None]:
        """Validate the API token by trying to fetch networks.

        Returns:
            Tuple of (success, error_message)
        """
        session = async_get_clientsession(self.hass)
        client = HafeleClient(api_token, session)

        try:
            networks = await client.get_networks()
            if not networks:
                return False, "no_networks_found"
            self._networks = [
                {
                    "id": network.id,
                    "name": network.name,
                    "device_count": len(
                        await client.get_devices_for_network(network.id)
                    ),
                }
                for network in networks
            ]
            return True, None
        except HafeleAPIError as err:
            _LOGGER.error("Failed to connect to Häfele API: %s", err)
            if "401" in str(err):
                return False, "invalid_auth"
            return False, "cannot_connect"
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error occurred: %s", err)
            return False, "unknown"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            api_token = user_input[CONF_API_TOKEN]
            valid, error = await self._validate_api_token(api_token)

            if valid:
                self._api_token = api_token
                return await self.async_step_network()

            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle network selection."""
        errors = {}

        if user_input is not None:
            network_id = user_input[CONF_NETWORK_ID]
            selected_network = next(
                (net for net in self._networks if net["id"] == network_id), None
            )

            if selected_network:
                return self.async_create_entry(
                    title=selected_network["name"],
                    data={
                        CONF_API_TOKEN: self._api_token,
                        CONF_NETWORK_ID: network_id,
                    },
                )

            errors["base"] = "network_not_found"

        network_schema = {
            vol.Required(CONF_NETWORK_ID): vol.In(
                {
                    net["id"]: f"{net['name']} ({net['device_count']} devices)"
                    for net in self._networks
                }
            ),
        }

        return self.async_show_form(
            step_id="network",
            data_schema=vol.Schema(network_schema),
            errors=errors,
        )
