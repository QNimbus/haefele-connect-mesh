"""Group model for Häfele Connect Mesh."""

from dataclasses import dataclass
from typing import List, Dict, Any
from ..exceptions import ValidationError
from .device import Device


class Group:
    """Represents a Häfele Connect Mesh group."""

    def __init__(
        self, id: str, network_id: str, name: str, device_ids: List[str]
    ) -> None:
        """Initialize a Group instance.

        Args:
            id: Group ID
            network_id: Network ID
            name: Group name
            device_ids: List of device IDs
        """
        self._id = id
        self._network_id = network_id
        self._name = name
        self._device_ids = device_ids
        self._devices = []

    @property
    def id(self) -> str:
        """Get the group ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the group name."""
        return self._name

    @property
    def network_id(self) -> str:
        """Get the network ID."""
        return self._network_id

    @property
    def device_ids(self) -> List[str]:
        """Get the list of device IDs."""
        return self._device_ids

    @property
    def device_count(self) -> int:
        """Get the number of devices in the group."""
        return len(self._device_ids)

    @property
    def devices(self) -> List[Device]:
        """Get the list of devices in the group."""
        return self._devices

    @devices.setter
    def devices(self, devices: List[Device]) -> None:
        """Set the list of devices in the group."""
        self._devices = devices

    @property
    def is_light(self) -> bool:
        """Check if the group is a light group."""
        return all(device.is_light for device in self._devices)

    @property
    def is_switch(self) -> bool:
        """Check if the group is a switch group."""
        return all(device.is_switch for device in self._devices)

    @property
    def is_sensor(self) -> bool:
        """Check if the group is a sensor group."""
        return all(device.is_sensor for device in self._devices)

    @property
    def supports_color_temp(self) -> bool:
        """Check if the group supports color temperature."""
        return all(device.supports_color_temp for device in self._devices)

    @property
    def supports_hsl(self) -> bool:
        """Check if the group supports HSL color."""
        return all(device.supports_hsl for device in self._devices)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Group":
        """Create a Group instance from dictionary data.

        Args:
            data: Dictionary containing group data from API

        Returns:
            Group instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        try:
            return cls(
                id=data["id"].lower(),
                network_id=data["networkId"].lower(),
                name=data["name"],
                device_ids=[
                    device["deviceId"].lower()
                    for device in data.get("deviceEntries", [])
                ],
            )
        except KeyError as e:
            raise ValidationError(f"Invalid group data: Missing field {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the group instance to a dictionary.

        Returns:
            Dictionary representation of the group
        """
        return {
            "id": self.id,
            "networkId": self.network_id,
            "name": self.name,
            "devices": self.devices,
        }
