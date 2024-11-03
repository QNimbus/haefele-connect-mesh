"""Constants for the Häfele Connect Mesh integration."""

NAME = "Häfele Connect Mesh"
DOMAIN = "haefele_connect_mesh"
VERSION = "0.1.0"

# Configuration
CONF_NETWORK_ID = "network_id"

# Device Capabilities

BRIGHTNESS_SCALE_PERCENTAGE = (1, 100)  # Percentage
BRIGHTNESS_SCALE_HA = (1, 255)  # Home Assistant brightness scale
BRIGHTNESS_SCALE_MESH = (1, 65535)  # Mesh brightness scale
MIN_KELVIN = 2000  # Minimum color temperature in Kelvin
MAX_KELVIN = 6500  # Maximum color temperature in Kelvin
MIN_MIREDS = 153  # Minimum color temperature in mireds
MAX_MIREDS = 500  # Maximum color temperature in mireds
