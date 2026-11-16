"""Per-model advertisement parsing and model → handler mapping."""
from __future__ import annotations

import pytest

from custom_components.govee_ble_hacs.scanner.device import (
    H50TH,
    H51TH,
    H507TH,
    H5179,
    H5183,
    H5184,
    MODEL_MAP,
    VALID_CLASSES,
    GoveeLight,
    determine_known_device,
)

from .conftest import advertisement, ble_device

PACKED = bytes([0x60, 0x09, 0x88, 0x13, 0x5A])  # 24.00 °C, 50.00 %, 90 %
ENCODED = bytes([0x03, 0xA0, 0xB4, 0x64])  # 23.77 °C, 74.8 %, 100 %


def test_every_model_maps_to_exactly_one_handler() -> None:
    """A model listed under two classes would be resolved arbitrarily."""
    assert sum(len(cls.SUPPORTED_MODELS) for cls in VALID_CLASSES) == len(MODEL_MAP)


@pytest.mark.parametrize(
    ("name", "cls", "key", "payload", "temp", "hum", "batt"),
    [
        ("Govee_H5074_0001", H50TH, 0xEC88, b"\x00" + PACKED, 24.0, 50.0, 90),
        ("GVH5179_0001", H5179, 0x8801, b"\x00" * 4 + PACKED, 24.0, 50.0, 90),
        ("GVH5075_0001", H507TH, 0xEC88, b"\x00" + ENCODED, 23.7748, 74.8, 100),
        ("GVH5102_0001", H51TH, 0x0001, b"\x00\x00" + ENCODED, 23.7748, 74.8, 100),
    ],
)
def test_thermo_hygrometers(name, cls, key, payload, temp, hum, batt) -> None:
    device = determine_known_device(ble_device(name), advertisement(key, payload))
    assert isinstance(device, cls)
    assert device.temperature == pytest.approx(temp)
    assert device.humidity == pytest.approx(hum)
    assert device.battery == batt


def test_packed_negative_temperature() -> None:
    payload = b"\x00" + bytes([0x38, 0xFF, 0x88, 0x13, 0x5A])  # -2.00 °C
    device = determine_known_device(ble_device("Govee_H5074_0001"), advertisement(0xEC88, payload))
    assert device.temperature == pytest.approx(-2.0)


def test_short_or_foreign_payload_is_ignored() -> None:
    device = determine_known_device(ble_device("GVH5075_0001"), advertisement(0xEC88, b"\x00\x03"))
    assert device.temperature is None
    device.update(ble_device("GVH5075_0001"), advertisement(0x1234, b"\x00" + ENCODED))
    assert device.temperature is None


def test_update_keeps_latest_reading() -> None:
    device = determine_known_device(ble_device("GVH5075_0001"), advertisement(0xEC88, b"\x00" + ENCODED))
    device.update(ble_device("GVH5075_0001"), advertisement(0xEC88, b"\x00" + bytes([0x81, 0x86, 0xA0, 0x32])))
    assert device.temperature == pytest.approx(-10.0)
    assert device.battery == 50


def test_bbq_probes() -> None:
    probes = bytes([0xC4, 0x09, 0xFF, 0xFF, 0x10, 0x27, 0xFF, 0xFF])  # 25.0, —, 100.0, —
    device = determine_known_device(ble_device("GVH5183_0001"), advertisement(0xEC88, b"\x00" + probes + b"\x4b"))
    assert isinstance(device, H5183)
    assert device.probe_temperatures == [25.0, None, 100.0, None]
    assert device.battery == 75


def test_bbq_missing_probe_bytes_are_none() -> None:
    device = determine_known_device(ble_device("GVH5184_0001"), advertisement(0xEC88, b"\x00\xc4\x09"))
    assert isinstance(device, H5184)
    assert device.probe_temperatures == [25.0, None, None, None, None, None]
    assert device.battery is None


def test_light_and_unknown_models() -> None:
    light = determine_known_device(ble_device("ihoment_H6001_0001"))
    assert isinstance(light, GoveeLight)
    assert light.dict() == {"address": "A4:C1:38:00:00:01", "name": "ihoment_H6001_0001", "model": "H6001"}
    assert determine_known_device(ble_device("GVH9999_0001"), advertisement(0xEC88, b"\x00")) is None
    assert determine_known_device(ble_device("Not a Govee")) is None
