"""Config flow, setup, discovery → entities, and unload."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.govee_ble_hacs.const import DOMAIN

from .conftest import advertisement, ble_device


async def test_config_flow_single_instance(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.govee_ble_hacs.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Govee BLE"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Govee BLE"

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_discovery_creates_device_and_sensors(hass: HomeAssistant) -> None:
    # The HA bluetooth stack isn't available in tests: mark it loaded and capture
    # the advertisement callback the scanner registers.
    hass.config.components.add("bluetooth")
    unsubscribe = MagicMock()
    with patch(
        "custom_components.govee_ble_hacs.scanner.async_register_callback", return_value=unsubscribe
    ) as register:
        entry = MockConfigEntry(domain=DOMAIN, title="Govee BLE", data={"name": "Govee BLE"})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    on_advertisement = register.call_args.args[1]

    def advertise(payload: bytes) -> None:
        on_advertisement(
            SimpleNamespace(device=ble_device("GVH5075_0001"), advertisement=advertisement(0xEC88, payload)),
            None,
        )

    advertise(b"\x00" + bytes([0x03, 0xA0, 0xB4, 0x64]))
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, "A4:C1:38:00:00:01"), entry.entry_id)
    assert device is not None
    assert device.model == "H5075"
    assert float(hass.states.get("sensor.gvh5075_0001_temperature").state) == 23.7748
    assert float(hass.states.get("sensor.gvh5075_0001_humidity").state) == 74.8
    assert hass.states.get("sensor.gvh5075_0001_battery").state == "100"

    # A later advertisement updates the existing entities
    advertise(b"\x00" + bytes([0x81, 0x86, 0xA0, 0x32]))
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.gvh5075_0001_temperature").state) == -10.0

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    unsubscribe.assert_called_once()
