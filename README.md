# HomeAssistant: Samsung Soundbar Integration

> Yet another Samsung Soundbar Integration (YASSI)

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

- Set-Up through HomeAssistant-UI
- Theoretically it should be possible to have multiple Devices (not tested)

- `media_player` Entity
  - On / Off
  - Volume
  - Mute
  - Input Source
  - Sound Mode
  - Media
    - Play / Pause / Stop
    - Artist
    - Title
    - Music Cover Art url (iTunes Api)
- `switch` entity
  - Night mode
  - Bass mode
  - Voice amplifier
- `number` entity
  - bass level
  - *[to come] equalizer bands*
- `select` entity
  - sound mode (additional control in the "Device" tab)
  - input (additional control in the "Device" tab)
  - equalizer preset

## How to install it:

### HACS: 
>  ⚠️ not done yet but planned (hopefully)

### Adding this repository as custom repository

Add this repository as custom repository in HACS and install it ;)

### Manual

You can also copy the `samsung_soundbar` folder in the `custom_components` folder to
your `config/custom_components` folder.


## General Thanks

Like already mentioned, thanks to @PiotrMachowski / @thierryBourbon for the general
idea on how to do things.