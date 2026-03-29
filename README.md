# Govee BLE Home Assistant Component

> **Fork of [natekspencer/hacs-govee_ble](https://github.com/natekspencer/hacs-govee_ble)** (archived Aug 2024)
> Maintained by [@linkian19](https://github.com/linkian19)

Home Assistant integration for Govee Bluetooth Low Energy (BLE) devices.

[![hacs][hacsbadge]][hacs]
[![License][license-shield]][license]

---

## ⚠️ Important Notes on This Fork

### What this integration does (and does not) do

This integration is **sensor-only** (read-only). It reads temperature, humidity, and battery data from Govee BLE thermometer/hygrometer devices by passively listening to BLE advertisements.

**It does NOT support:**
- Light control of any kind
- The H6181 LED light strip or any other Govee light device
- Any write/command capability

### BLE Proxy compatibility

This integration uses [Bleak](https://github.com/hbldh/python-bleak) to talk **directly to the system Bluetooth stack (BlueZ)**. It does **not** use Home Assistant's native Bluetooth integration layer, which means:

- **ESPHome BLE proxies are not supported** — the integration cannot see or use them
- A physical Bluetooth adapter accessible to the HA host is required
- If running HA OS in a VM (e.g. Proxmox), the host's BT adapter must be passed through to the VM

### Fork changelog

The original repository was archived and last updated September 2022. This fork applies the following fixes to restore compatibility with current Home Assistant (2023+):

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

---

## Supported Govee Devices

All supported devices are **temperature/humidity sensors**:

- [H5051][h5051]
- H5052
- [H5071][h5071]
- [H5072][h5072]
- [H5074][h5074]
- [H5075][h5075]
- [H5101][h5101]
- [H5102][h5102]
- [H5174][h5174]
- [H5177][h5177]
- [H5179][h5179]

**This component sets up the following platforms:**

| Platform | Description |
| -------- | ----------- |
| `sensor` | Temperature, Humidity, Battery, and Bluetooth Address for each discovered device |

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS** → **Integrations**
2. Click the vertical ellipsis (⋮) → **Custom repositories**
3. Enter `https://github.com/linkian19/hacs-govee_ble` and select category **Integration**
4. Click **ADD**, then install **Govee BLE** from the HACS integrations page
5. Restart Home Assistant

### Manual

1. Copy `custom_components/govee_ble/` into your HA config's `custom_components/` directory
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
    custom_components.govee_ble: debug
```

Only devices advertising names starting with `ihoment_`, `Govee_`, `Minger_`, `GBK_`, or `GVH` will be detected.

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
