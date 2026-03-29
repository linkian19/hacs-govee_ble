"""Govee BLE integration — sensors and lights via HA Bluetooth layer."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, EVENT_DEVICE_ADDED_TO_REGISTRY
from .helpers import get_scanner
from .scanner import DEVICE_DISCOVERED
from .scanner.device import Device, GoveeLight

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "light"]
DATA_START_PLATFORM_TASK = "start_platform_task"


@callback
def register_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    dev_reg: device_registry.DeviceRegistry,
    device: Device,
) -> None:
    """Register device in device registry."""
    params = DeviceInfo(
        identifiers={(DOMAIN, device.address)},
        name=device.name,
        model=device.model,
        manufacturer="Govee",
    )

    registered = dev_reg.async_get_or_create(config_entry_id=entry.entry_id, **params)
    async_dispatcher_send(hass, EVENT_DEVICE_ADDED_TO_REGISTRY, registered)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Govee BLE from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}

    scanner = get_scanner(hass, entry)
    dev_reg = device_registry.async_get(hass)

    @callback
    def async_on_device_discovered(device: Device) -> None:
        """Handle device discovered event."""
        _LOGGER.debug("Processing device %s", device)
        register_device(hass, entry, dev_reg, device)

        platform = "light" if isinstance(device, GoveeLight) else "sensor"
        async_dispatcher_send(
            hass,
            f"{DOMAIN}_{entry.entry_id}_add_{platform}",
            device,
        )

    async def start_platforms() -> None:
        """Start platforms and begin discovery."""
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        scanner.on(
            DEVICE_DISCOVERED, lambda event: async_on_device_discovered(event["device"])
        )
        scanner.start()

    platform_task = hass.async_create_task(start_platforms())
    hass.data[DOMAIN][entry.entry_id][DATA_START_PLATFORM_TASK] = platform_task

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    scanner = get_scanner(hass, entry)
    scanner.stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not unload_ok:
        return False

    info = hass.data[DOMAIN].pop(entry.entry_id)

    platform_task: asyncio.Task = info.get(DATA_START_PLATFORM_TASK)
    if platform_task and not platform_task.done():
        platform_task.cancel()
        try:
            await platform_task
        except asyncio.CancelledError:
            pass

    return True
