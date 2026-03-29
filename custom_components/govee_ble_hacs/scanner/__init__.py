from __future__ import annotations

import logging
from typing import Callable, Dict, List

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.core import HomeAssistant, callback

from .device import Device, determine_known_device
from .helpers import log_advertisement_message

_LOGGER = logging.getLogger(__name__)

DEVICE_DISCOVERED = "device discovered"


class Scanner:
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the scanner."""
        self._hass = hass
        self._listeners: Dict[str, List[Callable]] = {}
        self._known_devices: dict[str, Device] = {}
        self._unsubscribe: Callable | None = None

    @property
    def known_devices(self) -> list[Device]:
        return list(self._known_devices.values())

    def on(self, event_name: str, cb: Callable) -> Callable:
        """Register an event callback."""
        listeners: list = self._listeners.setdefault(event_name, [])
        listeners.append(cb)

        def unsubscribe() -> None:
            """Unsubscribe listeners."""
            if cb in listeners:
                listeners.remove(cb)

        return unsubscribe

    def emit(self, event_name: str, data: dict) -> None:
        """Run all callbacks for an event."""
        for listener in self._listeners.get(event_name, []):
            listener(data)

    def start(self) -> None:
        """Start scanning via HA bluetooth integration (proxy-compatible)."""

        @callback
        def _on_advertisement(
            service_info: BluetoothServiceInfoBleak, change: BluetoothChange
        ) -> None:
            device = service_info.device
            advertisement = service_info.advertisement
            log_advertisement_message(device, advertisement)
            known_device = self._known_devices.get(device.address)
            if known_device:
                known_device.update(device=device, advertisement=advertisement)
                self.emit(device.address, {"device": known_device})
            else:
                known_device = determine_known_device(
                    device=device, advertisement=advertisement
                )
                if known_device:
                    self._known_devices[device.address] = known_device
                    self.emit(DEVICE_DISCOVERED, {"device": known_device})

        self._unsubscribe = async_register_callback(
            self._hass,
            _on_advertisement,
            None,
            BluetoothScanningMode.PASSIVE,
        )

    def stop(self) -> None:
        """Stop scanning."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
