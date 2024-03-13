# YASSI: Yet Another Samsung Soundbar Integration (for Home Assistant)

Welcome to YASSI, the Home Assistant integration designed to bring comprehensive control over your Samsung Soundbar into your smart home ecosystem.

**Table of Contents:**
<!-- TOC -->
* [Why YASSI](#why-yassi)
* [Features](#features)
* [Installation / Setup](#installation--setup)
  * [Prerequisites](#prerequisites)
  * [Installation:](#installation)
  * [Configuration](#configuration)
* [Support](#support)
* [Contributing](#contributing)
* [General Thanks](#general-thanks)
<!-- TOC -->

## Why YASSI

The current Samsung Soundbar Integration by @PiotrMachowski / @thierryBourbon are already pretty cool.
But I wanted it to appear as a device, and base the Foundation on the `pysmartthings` python package.

Additionally, I wanted full control over the *Soundmode* and more. So I tried out a few things with the API,
and found that also the **Subwoofer** as well as the **Equalizer** are controllable.

I created a new wrapper around the `pysmartthings.DeviceEntity` specifically set up for a Soundbar, and this
is the Result.

I hope to integrate also controls for **surround speaker** as well as **Space-Fit Sound**, but as these features
are not documented... ;) 

## Features


- **UI Setup**: You can easily set up your Soundbar through the UI.
- **Media Player Controls**: Power, volume, mute, source selection, and media controls are all at your fingertips.
- **Selectable Sound Modes**: Choose from various sound modes and inputs for optimal audio.
- **Subwoofer & Equalizer Adjustment**: Fine-tune your audio experience.
- **Switchable Enhancements**: Toggle features like night mode and voice amplification.
- **Customizable Bass Level**: Set the bass to your preference.
- **Multiple Devices**: should be theoretically possible but **not** tested

For the full feature list per entity type, please take a look at the [documentation](ha-samsung-soundbar.vercel.app) website.

## Installation / Setup

### Prerequisites

Before you begin, ensure you have the following:

- A Samsung Soundbar compatible with SmartThings.
- HomeAssistant installed and running.
- HACS (Home Assistant Community Store) for easy installation.

### Installation

1. Add this repository as a custom repository in HACS or manually copy the `samsung_soundbar` folder to the `custom_components` directory in your HomeAssistant configuration.
2. Restart HomeAssistant.

> [!NOTE]
> It is planned to add it to the public `HACS` repository list, but not done yet.

### Configuration

To integrate your Samsung Soundbar with HomeAssistant using YASSI, you'll need the following variables:

- **SmartThings API Key**: [Retrieve your API key from SmartThings Tokens.](https://account.smartthings.com/tokens)
- **Device ID**: [Find your device ID at SmartThings Devices.](https://my.smartthings.com/advanced/devices)
- **Device Name**: Choose a name for your soundbar to be recognized in HomeAssistant.
- **Max Volume**: Define the maximum volume level for the `media_player` slider (between `1` and `100`).

Please use the HomeAssistant UI to setup the integration, providing a yaml configuration in the `configuration.yaml`
should be possible but is not recommended.

## Support

For support, feature requests, or bug reporting, please visit the Issues section of this GitHub repository.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

## General Thanks

- Like already mentioned, thanks to @PiotrMachowski / @thierryBourbon for the general idea on how to do things.