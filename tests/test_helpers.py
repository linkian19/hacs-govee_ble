"""Model-name parsing and the raw value decoders."""
from __future__ import annotations

import pytest

from custom_components.govee_ble_hacs.scanner.helpers import (
    decode_temperature_and_humidity,
    get_govee_model,
    twos_complement,
)


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("GVH5075_ABCD", "H5075"),
        ("Govee_H5074_1A2B", "H5074"),
        ("ihoment_H6001_1A2B", "H6001"),
        ("Minger_H6002_1A2B", "H6002"),
        ("GBK_H6110_1A2B", "H6110"),
        ("Govee_H5074", None),  # needs three parts
        ("GVH5075", None),  # needs a suffix
        ("SomethingElse_H5075_1A2B", None),
        ("", None),
        (None, None),
    ],
)
def test_get_govee_model(name: str | None, model: str | None) -> None:
    assert get_govee_model(name) == model


def test_twos_complement() -> None:
    assert twos_complement(0x0960) == 2400
    assert twos_complement(0xFF38) == -200
    assert twos_complement(0x80, 8) == -128


def test_decode_temperature_and_humidity() -> None:
    # 0x03A0B4 = 237748 → 23.7748 °C, 74.8 %
    temp, hum = decode_temperature_and_humidity(bytes([0x03, 0xA0, 0xB4]))
    assert temp == pytest.approx(23.7748)
    assert hum == pytest.approx(74.8)
    # High bit set = negative: 0x0186A0 = 100000 → -10.0 °C, 0.0 %
    temp, hum = decode_temperature_and_humidity(bytes([0x81, 0x86, 0xA0]))
    assert temp == pytest.approx(-10.0)
    assert hum == pytest.approx(0.0)
