"""Support for Govee BLE lights."""
from __future__ import annotations

import asyncio
import logging
from functools import reduce

from bleak import BleakClient
from bleak.exc import BleakError

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .helpers import get_scanner
from .scanner import Scanner
from .scanner.device import GoveeLight

_LOGGER = logging.getLogger(__name__)

# Govee BLE GATT protocol constants
_GOVEE_WRITE_CHAR_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
_GOVEE_NOTIFY_CHAR_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"
_CMD_POWER = 0x01
_CMD_BRIGHTNESS = 0x04
_CMD_COLOR = 0x05
_QUERY_POWER = 0x01

# Color temperature range supported by most Govee light models
_MIN_KELVIN = 2000
_MAX_KELVIN = 9000

# Timeout waiting for state query notification response
_QUERY_TIMEOUT = 5.0


def _build_command(cmd: int, *params: int) -> bytearray:
    """Build a 20-byte Govee BLE command (0x33 prefix) with XOR checksum."""
    payload = [0x33, cmd] + list(params)
    payload += [0x00] * (19 - len(payload))
    payload.append(reduce(lambda a, b: a ^ b, payload))
    return bytearray(payload)


def _build_query(cmd: int) -> bytearray:
    """Build a 20-byte Govee BLE state query (0xAA prefix) with XOR checksum."""
    payload = [0xAA, cmd]
    payload += [0x00] * 18
    payload.append(reduce(lambda a, b: a ^ b, payload))
    return bytearray(payload)


async def _send_command(hass: HomeAssistant, address: str, cmd: bytearray) -> bool:
    """Look up the BLE device (via HA bluetooth layer) and write a GATT command."""
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if not ble_device:
        _LOGGER.warning(
            "Cannot find connectable BLE device for %s — is a BLE proxy available?",
            address,
        )
        return False
    try:
        async with BleakClient(ble_device) as client:
            await client.write_gatt_char(_GOVEE_WRITE_CHAR_UUID, cmd, response=False)
        return True
    except BleakError as ex:
        _LOGGER.error("Failed to send command to %s: %s", address, ex)
        return False


async def _query_state(hass: HomeAssistant, address: str) -> dict | None:
    """
    Query the current state of a Govee light via GATT notification.

    Returns a dict with keys:
      is_on (bool), brightness (int 0-255),
      rgb (tuple|None), color_temp_kelvin (int|None)

    Response notification format (0xAA 0x01):
      byte 0: 0xAA
      byte 1: 0x01 (echoed sub-command)
      byte 2: power state — 0x00=off, 0x01=on
      byte 3: brightness 0-100
      byte 4: color mode — 0x01=white/color-temp, 0x02=RGB
      bytes 5-6: kelvin (big-endian) when mode=0x01
      bytes 5-7: R, G, B when mode=0x02
    """
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if not ble_device:
        return None

    result: dict | None = None
    response_event = asyncio.Event()

    def _on_notification(sender, data: bytearray) -> None:
        nonlocal result
        if len(data) >= 4 and data[0] == 0xAA and data[1] == _QUERY_POWER:
            is_on = data[2] == 0x01
            brightness = int(data[3] / 100 * 255)
            rgb = None
            color_temp_kelvin = None
            if len(data) >= 7:
                if data[4] == 0x01:  # white / color temp mode
                    color_temp_kelvin = (data[5] << 8) | data[6]
                elif data[4] == 0x02 and len(data) >= 8:  # RGB mode
                    rgb = (data[5], data[6], data[7])
            result = {
                "is_on": is_on,
                "brightness": brightness,
                "rgb": rgb,
                "color_temp_kelvin": color_temp_kelvin,
            }
            response_event.set()

    try:
        async with BleakClient(ble_device) as client:
            await client.start_notify(_GOVEE_NOTIFY_CHAR_UUID, _on_notification)
            await client.write_gatt_char(
                _GOVEE_WRITE_CHAR_UUID,
                _build_query(_QUERY_POWER),
                response=False,
            )
            try:
                await asyncio.wait_for(response_event.wait(), timeout=_QUERY_TIMEOUT)
            except asyncio.TimeoutError:
                _LOGGER.debug("State query timed out for %s", address)
            await client.stop_notify(_GOVEE_NOTIFY_CHAR_UUID)
    except BleakError as ex:
        _LOGGER.debug("State query failed for %s: %s", address, ex)

    return result


class GoveeBLELightEntity(LightEntity, RestoreEntity):
    """Representation of a Govee BLE light."""

    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = _MIN_KELVIN
    _attr_max_color_temp_kelvin = _MAX_KELVIN

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
        self._attr_color_temp_kelvin: int | None = None
        self._attr_color_mode: ColorMode = ColorMode.RGB

    async def async_added_to_hass(self) -> None:
        """Restore last known state, then try a live GATT query in the background."""
        # 1. Restore from HA state history — instant, no BLE connection needed
        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_is_on = last_state.state == STATE_ON
            if (bri := last_state.attributes.get(ATTR_BRIGHTNESS)) is not None:
                self._attr_brightness = bri
            if (rgb := last_state.attributes.get(ATTR_RGB_COLOR)) is not None:
                self._attr_rgb_color = tuple(rgb)
            if (ct := last_state.attributes.get(ATTR_COLOR_TEMP_KELVIN)) is not None:
                self._attr_color_temp_kelvin = ct
            color_mode_str = last_state.attributes.get("color_mode")
            if color_mode_str == ColorMode.COLOR_TEMP:
                self._attr_color_mode = ColorMode.COLOR_TEMP
            else:
                self._attr_color_mode = ColorMode.RGB
            _LOGGER.debug(
                "Restored state for %s: on=%s brightness=%s rgb=%s color_temp=%sK",
                self._device.address,
                self._attr_is_on,
                self._attr_brightness,
                self._attr_rgb_color,
                self._attr_color_temp_kelvin,
            )

        # 2. Register advertisement update callback
        self.async_on_remove(
            self._scanner.on(
                self._device.address,
                lambda event: self._update_callback(event["device"]),
            )
        )

        # 3. Best-effort live GATT query — background, won't block startup
        self.hass.async_create_task(self._async_poll_initial_state())

    async def _async_poll_initial_state(self) -> None:
        """Query device for current state and update if successful."""
        state = await _query_state(self.hass, self._device.address)
        if state is None:
            return
        self._attr_is_on = state["is_on"]
        self._attr_brightness = state["brightness"]
        if state["color_temp_kelvin"] is not None:
            self._attr_color_temp_kelvin = state["color_temp_kelvin"]
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif state["rgb"] is not None:
            self._attr_rgb_color = state["rgb"]
            self._attr_color_mode = ColorMode.RGB
        _LOGGER.debug(
            "Live state for %s: on=%s brightness=%s rgb=%s color_temp=%sK",
            self._device.address,
            self._attr_is_on,
            self._attr_brightness,
            self._attr_rgb_color,
            self._attr_color_temp_kelvin,
        )
        self.async_write_ha_state()

    @callback
    def _update_callback(self, device: GoveeLight) -> None:
        """Handle device advertisement update."""
        self._device = device
        self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on and optionally set brightness, RGB color, or color temperature."""
        if not self._attr_is_on:
            if not await _send_command(
                self.hass, self._device.address, _build_command(_CMD_POWER, 0x01)
            ):
                return
            self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            bri_pct = max(1, int(brightness / 255 * 100))
            if await _send_command(
                self.hass,
                self._device.address,
                _build_command(_CMD_BRIGHTNESS, bri_pct),
            ):
                self._attr_brightness = brightness

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            # White/color-temp mode: RGB set to full white, followed by kelvin (big-endian)
            if await _send_command(
                self.hass,
                self._device.address,
                _build_command(_CMD_COLOR, 0x02, 0xFF, 0xFF, 0xFF, kelvin >> 8, kelvin & 0xFF),
            ):
                self._attr_color_temp_kelvin = kelvin
                self._attr_color_mode = ColorMode.COLOR_TEMP

        elif ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            if await _send_command(
                self.hass,
                self._device.address,
                _build_command(_CMD_COLOR, 0x02, r, g, b),
            ):
                self._attr_rgb_color = (r, g, b)
                self._attr_color_mode = ColorMode.RGB

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
