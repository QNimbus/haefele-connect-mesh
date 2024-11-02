"""Platform for Häfele Connect Mesh light integration."""

from __future__ import annotations

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Häfele Connect Mesh Light platform."""
    # TODO: Implement light setup
    pass


class HaefeleConnectMeshLight(LightEntity):
    """Representation of a Häfele Connect Mesh Light."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self) -> None:
        """Initialize the light."""
        self._attr_unique_id = None  # TODO: Implement unique ID
        self._attr_name = None  # TODO: Implement name
        self._attr_brightness = None

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        # TODO: Implement turn on functionality
        pass

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        # TODO: Implement turn off functionality
        pass
