# Govee BLE Home Assistant Component

> **Fork of [natekspencer/hacs-govee_ble](https://github.com/natekspencer/hacs-govee_ble)** (archived Aug 2024)
> Maintained by [@linkian19](https://github.com/linkian19)

Home Assistant integration for Govee Bluetooth Low Energy (BLE) devices — temperature/humidity sensors, BBQ thermometers, and light strips.

[![hacs][hacsbadge]][hacs]
[![License][license-shield]][license]

---

## Supported Devices

### Temperature/Humidity Sensors

| Platform | Entities |
|----------|----------|
| `sensor` | Temperature, Humidity, Battery, Bluetooth Address |

- [H5051][h5051], H5052
- [H5071][h5071], [H5072][h5072], [H5074][h5074], [H5075][h5075]
- [H5101][h5101], [H5102][h5102], [H5174][h5174], [H5177][h5177]
- [H5179][h5179]

---

### BBQ / Meat Thermometers *(experimental)*

| Platform | Entities |
|----------|----------|
| `sensor` | Probe 1–N Temperature, Battery |

- H5183 (4 probes)
- H5184, H5185 (6 probes)

Each connected probe gets its own temperature sensor entity. Disconnected probes show as unavailable.

> **Note:** BBQ thermometer data parsing is based on community reverse-engineering and is marked experimental. If probe temperatures look wrong, please open an issue with your device's advertisement data from the debug log.

---

### Light Strips, Bulbs & Lamps

| Platform | Entities |
|----------|----------|
| `light` | On/off, Brightness (0–100%), RGB Color, Color Temperature (2000–9000 K) |

**H60xx — bulbs and early strips:**
H6001, H6002, H6003, H6004, H6008, H6009, H6010, H6011, H6013, H6015, H6016, H6017, H6018

**H602x — outdoor strips:**
H6025

**H604x — TV backlights:**
H6046, H6047, H6049

**H605x — floor lamps:**
H6051, H6052, H6053, H6054

**H605x–H606x — outdoor lights:**
H6059, H6061, H6062, H6065, H6066, H6067

**H607x — ceiling lights:**
H6071, H6072, H6073, H6076, H6078

**H608x — table lamps:**
H6085, H6086, H6087, H6088, H6089

**H609x–H610x — LED strips:**
H6099, H6102, H6104, H6107

**H611x — neon / rope strips:**
H6110, H6112, H6113, H6114, H6115, H6116, H6117, H6118, H6119

**H612x–H614x — LED strips:**
H6121, H6122, H6123, H6125, H6126, H6127,
H6130, H6131, H6133, H6134, H6135, H6136, H6137, H6138, H6139,
H6141, H6142, H6143, H6144, H6145, H6146, H6148

**H615x–H619x — LED strips:**
H6159, H6160, H6163, H6166, H6168, H6170, H6172,
H6175, H6176, H6177, H6178, H6179,
H6181, H6182, H6188, H6189, H6195, H6198

**H70xx — ceiling / panel lights:**
H7000, H7001, H7002, H7003, H7004, H7005, H7006

**H701x–H703x — LED strips:**
H7010, H7011, H7012, H7013, H7014, H7015, H7016, H7017, H7018, H7019,
H7020, H7021, H7022, H7023, H7024, H7025, H7026, H7028,
H7030, H7031, H7032, H7033, H7035, H7036, H7037, H7038

**H704x–H706x — LED strips:**
H7041, H7042, H7043, H7044, H7045, H7046, H7047,
H7050, H7055, H7060, H7061, H7062, H7065

> **Note:** All light models share the same Govee GATT BLE protocol. Models inferred from the H6xxx/H7xxx product family that have not been physically tested are still expected to work, but if you run into issues please open an issue.

---

## BLE Proxy Support

This integration uses **Home Assistant's native Bluetooth integration layer** — it does not talk directly to BlueZ. This means:

- **ESPHome BLE proxies are fully supported**
- No physical Bluetooth adapter on the HA host is required (a proxy is sufficient)
- Passive scanning (advertisement sniffing) works through proxies for sensor devices
- Active connections (GATT commands for lights) route through connectable proxies

Minimum Home Assistant version: **2022.8** (when the HA Bluetooth layer shipped).

---

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS** → **Integrations**
2. Click the vertical ellipsis (⋮) → **Custom repositories**
3. Enter `https://github.com/linkian19/hacs-govee_ble` and select category **Integration**
4. Click **ADD**, then install **Govee BLE (HACS)** from the HACS integrations page
5. Restart Home Assistant

### Manual

1. Copy `custom_components/govee_ble_hacs/` into your HA config's `custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for **Govee BLE** and follow the config flow

## Debugging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.govee_ble_hacs: debug
```

Only devices advertising names starting with `ihoment_`, `Govee_`, `Minger_`, `GBK_`, or `GVH` will be detected.

---

## Fork Changelog

The original repository was archived and last updated September 2022. This fork applies the following fixes and enhancements:

### Compatibility fixes (deprecated HA APIs)

| Fix | File | Details |
|-----|------|---------|
| `async_get_registry()` removed | `__init__.py` | Replaced with synchronous `async_get()` |
| `async_forward_entry_setup()` removed | `__init__.py` | Replaced with `async_forward_entry_setups()` |
| `async_forward_entry_unload()` removed | `__init__.py` | Replaced with `async_unload_platforms()` |
| `CONN_CLASS_LOCAL_PUSH` removed | `config_flow.py` | Removed deprecated `CONNECTION_CLASS` attribute |
| `TEMP_CELSIUS` deprecated | `sensor.py` | Replaced with `UnitOfTemperature.CELSIUS` |
| `abstractstaticmethod` deprecated | `scanner/device.py` | Replaced with `@staticmethod` + `@abstractmethod` |
| Missing `self` in `dict()` | `scanner/device.py` | Fixed abstract method signature |
| Potential `NoneType` crash | `scanner/device.py` | Added null check for `advertisement` argument |

### New features

| Change | Details |
|--------|---------|
| Domain renamed to `govee_ble_hacs` | Prevents conflict with HA's built-in `govee_ble` integration |
| BLE proxy support | Scanner rewritten to use `async_register_callback` via HA Bluetooth layer instead of direct `BleakScanner` |
| Light platform added | `light.py` with Govee GATT protocol — power, brightness, RGB color, color temperature |
| Color temperature support | Lights support warm/cool white (2000–9000 K) in addition to RGB color |
| Expanded light model list | 90+ H6xxx/H7xxx models covering bulbs, strips, lamps, ceiling lights, and TV backlights |
| BBQ thermometer support | H5183 (4 probes), H5184/H5185 (6 probes) — one sensor entity per probe |
| State restoration | Light entities restore last known state from HA history on startup |
| Live state polling | On startup, a background GATT query fetches actual device state; overrides restored state if successful |

---

## Credits

Original integration by [@natekspencer](https://github.com/natekspencer).
Based on work from [Home-Is-Where-You-Hang-Your-Hack/sensor.goveetemp_bt_hci][goveetemp_bt_hci], [irremotus/govee][govee], and [asednev/govee-bt-client][govee-bt-client].

---

[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license]: https://github.com/linkian19/hacs-govee_ble/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/linkian19/hacs-govee_ble.svg?style=for-the-badge
[goveetemp_bt_hci]: https://github.com/Home-Is-Where-You-Hang-Your-Hack/sensor.goveetemp_bt_hci
[govee]: https://github.com/irremotus/govee
[govee-bt-client]: https://github.com/asednev/govee-bt-client
[h5051]: https://www.amazon.com/dp/B07FBCTQ3L
[h5071]: https://www.amazon.com/dp/B07TWMSNH5
[h5072]: https://www.amazon.com/dp/B07DWMJKP5
[h5074]: https://www.amazon.com/dp/B07R586J37
[h5075]: https://www.amazon.com/dp/B0872X4H4J
[h5101]: https://www.amazon.com/dp/B08CGM8DC7
[h5102]: https://www.amazon.com/dp/B087313N8F
[h5174]: https://www.amazon.com/dp/B08JLNXLVZ
[h5177]: https://www.amazon.com/dp/B08C9VYMHY
[h5179]: https://www.amazon.com/dp/B0872ZWV8X
