"""Device models for the Häfele Connect Mesh API."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from ..exceptions import ValidationError
from datetime import datetime


@dataclass
class Element:
    """Represents a device element in the mesh network.

    Elements are the basic building blocks of mesh devices, each representing
    a controllable component of the device.
    """

    device_id: str
    unicast_address: int
    models: List[int]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Element":
        """Create an Element instance from dictionary data.

        Args:
            data: Dictionary containing element data

        Returns:
            Element instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        try:
            return cls(
                device_id=data["deviceId"],
                unicast_address=int(data["unicastAddress"]),
                models=[int(model) for model in data["models"]],
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValidationError(f"Invalid element data: {str(e)}")


class Device:
    """Represents a Häfele Connect Mesh device.

    Attributes:
        network_id: UUID of the network the device belongs to
        unicast_address: Device mesh address
        id: Object ID
        name: User-defined device name
        description: Device description
        ble_address: Bluetooth address
        mac_bytes: MAC address bytes
        bootloader_version: Device firmware version
        type: Device type identifier (e.g., 'com.haefele.led.rgb')
        unique_id: Unique device identifier
        device_key: Device encryption key
        elements: List of device mesh elements
    """

    def __init__(
        self,
        network_id: str,
        unicast_address: int,
        id: str,
        name: str,
        description: Optional[str],
        ble_address: str,
        mac_bytes: str,
        bootloader_version: str,
        type: str,
        unique_id: str,
        device_key: str,
        elements: List[Element],
    ) -> None:
        """Initialize a Device instance.

        Args:
            network_id: UUID of the network the device belongs to
            unicast_address: Device mesh address
            id: Object ID
            name: User-defined device name
            description: Device description
            ble_address: Bluetooth address
            mac_bytes: MAC address bytes
            bootloader_version: Device firmware version
            type: Device type identifier
            unique_id: Unique device identifier
            device_key: Device encryption key
            elements: List of device mesh elements
        """
        self._network_id = network_id
        self._unicast_address = unicast_address
        self._id = id
        self._name = name
        self._description = description
        self._ble_address = ble_address
        self._mac_bytes = mac_bytes
        self._bootloader_version = bootloader_version
        self._type = type
        self._unique_id = unique_id
        self._device_key = device_key
        self._elements = elements
        self._last_updated = datetime.utcnow()

    @property
    def network_id(self) -> str:
        """Get the network ID."""
        return self._network_id

    @property
    def unicast_address(self) -> int:
        """Get the unicast address."""
        return self._unicast_address

    @property
    def id(self) -> str:
        """Get the device ID (alias for unique_id)."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Get the device name."""
        return self._name

    @property
    def description(self) -> Optional[str]:
        """Get the device description."""
        return self._description

    @property
    def ble_address(self) -> str:
        """Get the Bluetooth address."""
        return self._ble_address

    @property
    def mac_bytes(self) -> str:
        """Get the MAC address bytes."""
        return self._mac_bytes

    @property
    def bootloader_version(self) -> str:
        """Get the bootloader version."""
        return self._bootloader_version

    @property
    def type(self) -> str:
        """Get the device type."""
        return self._type

    @property
    def device_key(self) -> str:
        """Get the device key."""
        return self._device_key

    @property
    def elements(self) -> List[Element]:
        """Get the device elements."""
        return self._elements

    @property
    def last_updated(self) -> datetime:
        """Get the timestamp of the last update to this device instance."""
        return self._last_updated

    def update_timestamp(self) -> None:
        """Update the last_updated timestamp to current time."""
        self._last_updated = datetime.utcnow()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """Create a Device instance from dictionary data.

        Args:
            data: Dictionary containing device data from API

        Returns:
            Device instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        try:
            return cls(
                network_id=data["networkId"],
                unicast_address=int(data["unicastAddress"]),
                id=data["id"],
                name=data["name"],
                description=data.get("description"),
                ble_address=data["bleAddress"],
                mac_bytes=data["macBytes"],
                bootloader_version=data["bootloaderVersion"],
                type=data["type"],
                unique_id=data["uniqueId"],
                device_key=data["deviceKey"],
                elements=[Element.from_dict(elem) for elem in data["elements"]],
            )
        except (KeyError, ValueError) as e:
            raise ValidationError(f"Invalid device data: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the device instance to a dictionary.

        Returns:
            Dictionary representation of the device
        """
        return {
            "networkId": self._network_id,
            "unicastAddress": self._unicast_address,
            "id": self._id,
            "name": self._name,
            "description": self._description,
            "bleAddress": self._ble_address,
            "macBytes": self._mac_bytes,
            "bootloaderVersion": self._bootloader_version,
            "type": self._type,
            "uniqueId": self._unique_id,
            "deviceKey": self._device_key,
            "elements": [
                {
                    "deviceId": elem.device_id,
                    "unicastAddress": elem.unicast_address,
                    "models": elem.models,
                }
                for elem in self._elements
            ],
        }

    @property
    def is_light(self) -> bool:
        """Check if the device is a light.

        Returns:
            bool: True if device is a light type
        """
        return self._type.startswith("com.haefele.led")

    @property
    def is_switch(self) -> bool:
        """Check if the device is a switch.

        Returns:
            bool: True if device is a switch type
        """
        return self._type == "com.haefele.switch"

    @property
    def is_sensor(self) -> bool:
        """Check if the device is a sensor.

        Returns:
            bool: True if device is a sensor type
        """
        return self._type.startswith("com.haefele.sensor")
