"""Config flow for Häfele Connect Mesh integration."""

from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_NETWORK_ID, CONF_SCAN_INTERVAL, CONF_NEW_DEVICES_CHECK_INTERVAL, CONF_DEVICE_DETAILS_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL, DEFAULT_NEW_DEVICES_CHECK_INTERVAL, DEFAULT_DEVICE_DETAILS_UPDATE_INTERVAL
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
        client = HafeleClient(api_token, session, timeout=6)

        try:
            networks = await client.get_networks()
            if not networks:
                return False, "no_networks_found"

            # Get device counts for each network
            self._networks = []
            for network in networks:
                devices = await client.get_devices_for_network(network.id)
                self._networks.append(
                    {
                        "id": network.id,
                        "name": network.name,
                        "device_count": len(devices),
                    }
                )
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

        # Create network options with placeholders for translation
        network_options = {
            net["id"]: f"{net['name']} ({net['device_count']})"
            for net in self._networks
        }

        network_schema = {
            vol.Required(CONF_NETWORK_ID): vol.In(network_options),
        }

        placeholders = {
            "device_count": str(sum(net["device_count"] for net in self._networks)),
        }

        return self.async_show_form(
            step_id="network",
            data_schema=vol.Schema(network_schema),
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> HafeleOptionsFlowHandler:
        """Create the options flow."""
        return HafeleOptionsFlowHandler()

    async def async_migrate_entry(self, config_entry: ConfigEntry) -> bool:
        """Migrate old entry."""
        _LOGGER.debug("Migrating from version %s", config_entry.version)

        if config_entry.version == 1:
            # No migration needed yet
            return True

        return False

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauthorization request."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthorization confirmation."""
        errors = {}
        
        if user_input is not None:
            api_token = user_input[CONF_API_TOKEN]
            valid, error = await self._validate_api_token(api_token)

            if valid:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_API_TOKEN: api_token},
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_API_TOKEN): str,
            }),
            errors=errors,
            description_placeholders={
                "error_detail": errors.get("base", "")
            },
        )


class HafeleOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Häfele Connect Mesh options."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._conf_app_id: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
            vol.Optional(
                CONF_NEW_DEVICES_CHECK_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_NEW_DEVICES_CHECK_INTERVAL, DEFAULT_NEW_DEVICES_CHECK_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            vol.Optional(
                CONF_DEVICE_DETAILS_UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_DEVICE_DETAILS_UPDATE_INTERVAL, DEFAULT_DEVICE_DETAILS_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options),
        )
