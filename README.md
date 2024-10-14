# YASSI: Yet Another Samsung Soundbar Integration (for Home Assistant)

Welcome to YASSI, the Home Assistant integration designed to bring comprehensive control over your Samsung Soundbar into your smart home ecosystem.

> [!NOTE]
> Please use service calls for setting the attribute of a custom capability instead of the entity. (See #43 for more information)

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
- Home Assistant installed and running.
- HACS (Home Assistant Community Store) for easy installation.

### Installation

1. Add this repository as a custom repository in HACS or manually copy the `samsung_soundbar` folder to the `custom_components` directory in your Home Assistant configuration.

  [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=samuelspagl&repository=ha_samsung_soundbar&category=integration)
2. Restart Home Assistant.

> [!NOTE]
> It is planned to add it to the default `HACS` repository list, but not done yet.

### Configuration

To integrate your Samsung Soundbar with Home Assistant using YASSI, you will be asked for the following variables:

- **SmartThings API Key**: [Retrieve your API key from SmartThings Tokens.](https://account.smartthings.com/tokens)
- **Device ID**: [Find your device ID at SmartThings Devices.](https://my.smartthings.com/advanced/devices)
- **Device Name**: Choose a name for your soundbar to be recognized in Home Assistant.
- **Max Volume**: Define the maximum volume level for the `media_player` slider (between `1` and `100`).

## Support

For support, feature requests, or bug reporting, please visit the Issues section of this GitHub repository.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

## General Thanks

- Like already mentioned, thanks to @PiotrMachowski / @thierryBourbon for the general idea on how to do things.
