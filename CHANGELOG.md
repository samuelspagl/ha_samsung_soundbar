# Changelog

## [0.3.1] Documentation enhancements

### Changed

- Updated the `README` as well as the documentation website

## [0.3.0] Icons and Chore

### Added

- Icons for the individual entities

### Changed

- Updated the GitHub actions workflows
- Change "magic numbers" to `MediaPlayerEntityFeature` object
  For more information see https://developers.home-assistant.io/blog/2023/12/28/support-feature-magic-numbers-deprecation
- the `source` now returns the value `wifi` when the `media_app_name` is `AirPlay` or `Spotify`
- removed some unnecessary logging statements, and changed others to `debug`

## [0.2.1] Chore: Format repository - 2024-02-08

### Changed

- formatted the repository with black and isort

## [0.2.0] Add volume sensor - 2024-02-08

### Added

- add new sensor entity for the volume
  
### Fix

- remove `extra_state_attributes` from `media_player` instance:
  The property caused some unwanted side-effects on some systems.

## [0.1.0] 🎉 First Version

### Added

- first version, gonna extend this Changelog sometime :D