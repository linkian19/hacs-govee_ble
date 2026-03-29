"""Support for Govee BLE lights."""
from __future__ import annotations

import logging
from functools import reduce

from bleak import BleakClient
from bleak.exc import BleakError

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .helpers import get_scanner
from .scanner import Scanner
from .scanner.device import GoveeLight

_LOGGER = logging.getLogger(__name__)

# Govee BLE GATT protocol constants
_GOVEE_WRITE_CHAR_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
_CMD_POWER = 0x01
_CMD_BRIGHTNESS = 0x04
_CMD_COLOR = 0x05


def _build_command(cmd: int, *params: int) -> bytearray:
    """Build a 20-byte Govee BLE command with XOR checksum."""
    payload = [0x33, cmd] + list(params)
    payload += [0x00] * (19 - len(payload))
    payload.append(reduce(lambda a, b: a ^ b, payload))
    return bytearray(payload)


async def _send_command(hass: HomeAssistant, address: str, cmd: bytearray) -> bool:
    """Look up the BLE device (via HA bluetooth layer) and write a GATT command."""
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if not ble_device:
        _LOGGER.warning("Cannot find connectable BLE device for %s — is a BLE proxy available?", address)
        return False
    try:
        async with BleakClient(ble_device) as client:
            await client.write_gatt_char(_GOVEE_WRITE_CHAR_UUID, cmd, response=False)
        return True
    except BleakError as ex:
        _LOGGER.error("Failed to send command to %s: %s", address, ex)
        return False


class GoveeBLELightEntity(LightEntity):
    """Representation of a Govee BLE light."""

    _attr_should_poll = False
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, scanner: Scanner, device: GoveeLight) -> None:
        """Initialize the light entity."""
        self._scanner = scanner
        self._device = device
        self._attr_name = device.name
        self._attr_unique_id = device.address
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device.address)})
        self._attr_is_on: bool | None = None
        self._attr_brightness: int | None = None
        self._attr_rgb_color: tuple[int, int, int] | None = None

    async def async_added_to_hass(self) -> None:
        """Register update callback when entity is added."""
        self.async_on_remove(
            self._scanner.on(
                self._device.address,
                lambda event: self._update_callback(event["device"]),
            )
        )

    @callback
    def _update_callback(self, device: GoveeLight) -> None:
        """Handle device advertisement update."""
        self._device = device
        self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on and optionally set brightness/color."""
        if not self._attr_is_on:
            if not await _send_command(
                self.hass, self._device.address, _build_command(_CMD_POWER, 0x01)
            ):
                return
            self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            # HA brightness is 0-255; Govee expects 0-100
            bri_pct = max(1, int(brightness / 255 * 100))
            if await _send_command(
                self.hass,
                self._device.address,
                _build_command(_CMD_BRIGHTNESS, bri_pct),
            ):
                self._attr_brightness = brightness

        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            if await _send_command(
                self.hass,
                self._device.address,
                _build_command(_CMD_COLOR, 0x02, r, g, b),
            ):
                self._attr_rgb_color = (r, g, b)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        if await _send_command(
            self.hass, self._device.address, _build_command(_CMD_POWER, 0x00)
        ):
            self._attr_is_on = False
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Govee BLE lights from a config entry."""
    scanner = get_scanner(hass, entry)

    @callback
    def async_add_light(device: GoveeLight) -> None:
        """Add a newly discovered Govee light."""
        _LOGGER.debug("Adding light entity for %s", device)
        async_add_entities([GoveeBLELightEntity(scanner=scanner, device=device)])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_{entry.entry_id}_add_{LIGHT_DOMAIN}",
            async_add_light,
        )
    )
