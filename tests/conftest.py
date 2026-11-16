"""Shared fixtures and fakes for Govee BLE tests."""
from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


def ble_device(name: str | None, address: str = "A4:C1:38:00:00:01") -> SimpleNamespace:
    """Stand-in for bleak's BLEDevice (its constructor differs between bleak versions)."""
    return SimpleNamespace(address=address, name=name, rssi=-60)


def advertisement(key: int, data: bytes) -> SimpleNamespace:
    """Stand-in for bleak's AdvertisementData."""
    return SimpleNamespace(manufacturer_data={key: data})
