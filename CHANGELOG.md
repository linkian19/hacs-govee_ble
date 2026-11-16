# Changelog

All notable changes to this project will be documented in this file.

## 2026.11.0

- Minimum Home Assistant version corrected to 2022.11 (was listed as 2022.8, but the integration uses APIs added in 2022.11)
- Manifest declares `iot_class: local_push` and `integration_type: hub` (passes hassfest)
- `hacs.json`: removed keys HACS no longer accepts
- Internal: `Device.update` no longer mis-declared as a static method; modern typing and `TimeoutError`
- CI: ruff, hassfest, HACS validation and a pytest suite (25 tests) on every push

## 2021.7.1

- Remove references to H5053 since it only supports Wi-Fi

## 2021.7.0

- Fix for H5179 missing from valid classes

## 2021.4.2

- Add compatibility for more sensors

## 2021.4.1

- Fix humidity value on H5174 when temperature is negative

## 2021.4.0

- **Initial Release**
