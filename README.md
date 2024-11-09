# Häfele Connect Mesh Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

![Häfele](./custom_components/haefele_connect_mesh/logo/icon.png)

A Home Assistant custom integration for Häfele Connect Mesh devices. This integration allows you to control Häfele smart devices through Home Assistant.

## Supported Devices

Currently, this integration has been tested with:
- Häfele LED lights (dimmable)

While the integration includes support for color temperature and RGB/HSL capable lights, as well as other device types (switches, sensors, etc.), these features are currently **untested** as I don't have access to these device types.

## Prerequisites

- A working Häfele Connect Mesh setup ([Häfele Connect Mesh Gateway](https://www.hafele.nl/nl/product/gateway-haefele-connect-mesh/85000074))
- A Häfele Connect Mesh API token (Sign up for a [Connect Mesh Cloud](https://cloud.connect-mesh.io/developer) account and generate an API token)
- Home Assistant 2024.1.0 or newer

## Installation

### Using HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL of this repository
   - Select "Integration" as the category
3. Click "Install"
4. Restart Home Assistant

### Manual Installation

1. Copy the `haefele_connect_mesh` folder to your `custom_components` folder
2. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Häfele Connect Mesh"
4. Enter your API token
   - Navigate to [Connect Mesh Cloud](https://cloud.connect-mesh.io/developer) to create an account and generate an API token
   - You can manually interact with the API using the [Connect Mesh Web API](https://webapi.cloud.connect-mesh.io/api/) if you prefer
5. Select the network you want to add

## Features

- Automatic discovery of Häfele devices in your network
- Automatic periodic refresh of device information (i.e. names)
- Support for turning lights on/off
- Support for dimming lights
- Support for color temperature (untested)
- Support for RGB/HSL colors (untested)

## Limitations

- Color temperature and RGB/HSL features are untested
- Other device types (switches, sensors, etc.) are not yet implemented

## Contributing

Feel free to contribute to this project if you have access to other Häfele device types and can help test and improve the integration.

## Issues

If you find any bugs or have feature requests, please create an issue in this repository.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Disclaimer

This integration is not officially affiliated with or endorsed by Häfele. Use at your own risk.
