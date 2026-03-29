from __future__ import annotations

import abc
import logging
from struct import unpack_from
from typing import Optional, Type

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .attribute import Battery, Hygrometer, ProbeTemperatures, Thermometer
from .helpers import decode_temperature_and_humidity, get_govee_model, twos_complement

_LOGGER = logging.getLogger(__name__)


class Device(abc.ABC):
    SUPPORTED_MODELS: set[str] = None

    def __init__(
        self, device: BLEDevice, advertisement: Optional[AdvertisementData] = None
    ):
        """Initialize a device."""
        self._device = device
        self._model = get_govee_model(device.name)
        if advertisement:
            self.update(device, advertisement)

    @property
    def address(self) -> str:
        """Return the address of this device."""
        return self._device.address

    @property
    def name(self) -> str:
        """Return the name of this device."""
        return self._device.name

    @property
    def rssi(self) -> int:
        """Return the rssi of this device."""
        return self._device.rssi

    @property
    def model(self):
        """Return the model of this device."""
        return self._model

    @staticmethod
    @abc.abstractmethod
    def update(self, device: BLEDevice, advertisement: AdvertisementData):
        raise NotImplementedError()

    def update_device(self, device: BLEDevice):
        if self._device != device:
            self._device = device

    @abc.abstractmethod
    def dict(self):
        raise NotImplementedError()

    def __repr__(self):
        """Return pertinent data about this device."""
        return str(self.dict())


class UnsupportedDevice(Device):
    pass


class ThermoHygrometer(Device, Thermometer, Hygrometer, Battery):
    """Abstract Govee Thermo-Hygrometer Sensor Device."""

    MANUFACTURER_DATA_KEY: int = None
    OFFSET: int = None
    NUMBER_OF_BYTES: int = None

    def dict(self):
        """Return pertinent data about this device."""
        return {
            "address": self.address,
            "name": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
        }

    def update(self, device: BLEDevice, advertisement: AdvertisementData):
        """Update the device data from an advertisement."""
        self.update_device(device)

        update_data = advertisement.manufacturer_data.get(self.MANUFACTURER_DATA_KEY)
        if update_data and len(update_data) >= self.OFFSET + self.NUMBER_OF_BYTES:
            self.parse(update_data)

    @abc.abstractmethod
    def parse(self, data: bytes) -> None:
        """Parse the data."""
        raise NotImplementedError()


class ThermoHygrometerPacked(ThermoHygrometer):
    """Govee Thermo-Hygrometer Sensor with packed data for Temperature and Humidity."""

    NUMBER_OF_BYTES = 5

    def parse(self, data: bytes) -> None:
        """Parse the data."""
        temp, hum, batt = unpack_from("<HHB", data, self.OFFSET)
        self._temperature = float(twos_complement(temp) / 100)
        self._humidity = float(hum / 100)
        self._battery = int(batt)


class H50TH(ThermoHygrometerPacked):
    """
    Govee H50XX Thermo-Hygrometer Sensor.

    Supported Models:
    - H5051
    - H5052
    - H5071
    - H5074
    """

    SUPPORTED_MODELS = {"H5051", "H5052", "H5071", "H5074"}
    MANUFACTURER_DATA_KEY = 60552  # EC88
    OFFSET = 1


class H5179(ThermoHygrometerPacked):
    """
    Govee H5179 Thermo-Hygrometer Sensor.

    Supported Models:
    - H5179
    """

    SUPPORTED_MODELS = {"H5179"}
    MANUFACTURER_DATA_KEY = 34817  # 8801
    OFFSET = 4


class ThermoHygrometerEncoded(ThermoHygrometer):
    """Govee Thermo-Hygrometer Sensor with combined data for Temperature and Humidity."""

    NUMBER_OF_BYTES = 4

    def parse(self, data: bytes) -> None:
        """Parse the data."""
        self._temperature, self._humidity = decode_temperature_and_humidity(
            data[self.OFFSET : self.OFFSET + 3]
        )
        self._battery = int(data[self.OFFSET + 3])


class H507TH(ThermoHygrometerEncoded):
    """
    Govee H5072/5 Thermo-Hygrometer Sensor.

    Supported Models:
    - H5072
    - H5075
    """

    SUPPORTED_MODELS = {"H5072", "H5075"}
    MANUFACTURER_DATA_KEY = 60552  # EC88
    OFFSET = 1


class H51TH(ThermoHygrometerEncoded):
    """
    Govee H51XX Thermo-Hygrometer Sensor.

    Supported Models:
    - H5101
    - H5102
    - H5174
    - H5177
    """

    SUPPORTED_MODELS = {"H5101", "H5102", "H5174", "H5177"}
    MANUFACTURER_DATA_KEY = 1  # 0001
    OFFSET = 2


class GoveeBBQThermometer(Device, ProbeTemperatures, Battery):
    """
    Govee BLE BBQ/Meat Thermometer base class.

    Data format based on community reverse-engineering of H5183/H5184 BLE advertisements.
    Probe temps are 2-byte little-endian values in 0.01 °C units; 0xFFFF = probe not connected.

    NOTE: This parsing is experimental. If probes report incorrect values, the OFFSET or
    MANUFACTURER_DATA_KEY below may need adjustment for your specific unit.
    """

    MANUFACTURER_DATA_KEY = 60552  # EC88 — same key as H50TH/H507TH
    OFFSET = 1  # skip leading flags byte
    MAX_PROBES: int = 4

    def update(self, device: BLEDevice, advertisement: AdvertisementData) -> None:
        """Parse probe temperature data from advertisement."""
        self.update_device(device)
        data = advertisement.manufacturer_data.get(self.MANUFACTURER_DATA_KEY)
        if not data:
            return

        probes: list[float | None] = []
        for i in range(self.MAX_PROBES):
            offset = self.OFFSET + i * 2
            if len(data) >= offset + 2:
                raw = unpack_from("<H", data, offset)[0]
                probes.append(None if raw == 0xFFFF else round(raw / 100, 1))
            else:
                probes.append(None)
        self._probe_temperatures = probes

        bat_offset = self.OFFSET + self.MAX_PROBES * 2
        if len(data) > bat_offset:
            self._battery = int(data[bat_offset])

    def dict(self):
        """Return pertinent data about this device."""
        return {
            "address": self.address,
            "name": self.name,
            "model": self.model,
            "probe_temperatures": self.probe_temperatures,
            "battery": self.battery,
        }


class H5183(GoveeBBQThermometer):
    """Govee H5183 4-probe BBQ Thermometer."""

    SUPPORTED_MODELS = {"H5183"}
    MAX_PROBES = 4


class H5184(GoveeBBQThermometer):
    """Govee H5184/H5185 6-probe BBQ Thermometer."""

    SUPPORTED_MODELS = {"H5184", "H5185"}
    MAX_PROBES = 6


class GoveeLight(Device):
    """
    Govee BLE Light device (controllable via GATT).

    All models share the same service/characteristic UUIDs and command protocol.
    Models marked with (?) are inferred from the H6xxx/H7xxx BLE product family
    and may need validation on physical hardware.
    """

    SUPPORTED_MODELS = {
        # --- H60xx: basic bulbs / early strips ---
        "H6001", "H6002", "H6003", "H6004", "H6008", "H6009",
        "H6010", "H6011", "H6013", "H6015", "H6016", "H6017", "H6018",
        # --- H602x: outdoor strips ---
        "H6025",
        # --- H604x: TV backlights ---
        "H6046", "H6047", "H6049",
        # --- H605x: floor lamps ---
        "H6051", "H6052", "H6053", "H6054",
        # --- H605x-H606x: outdoor ---
        "H6059", "H6061", "H6062", "H6065", "H6066", "H6067",
        # --- H607x: ceiling lights ---
        "H6071", "H6072", "H6073", "H6076", "H6078",
        # --- H608x: table lamps ---
        "H6085", "H6086", "H6087", "H6088", "H6089",
        # --- H609x / H610x: misc strips ---
        "H6099", "H6102", "H6104", "H6107",
        # --- H611x: neon / rope strips ---
        "H6110", "H6112", "H6113", "H6114", "H6115", "H6116", "H6117",
        "H6118", "H6119",
        # --- H612x-H614x: LED strips ---
        "H6121", "H6122", "H6123", "H6125", "H6126", "H6127",
        "H6130", "H6131", "H6133", "H6134", "H6135", "H6136", "H6137",
        "H6138", "H6139",
        "H6141", "H6142", "H6143", "H6144", "H6145", "H6146", "H6148",
        # --- H615x-H617x: LED strips ---
        "H6159", "H6160", "H6163",
        "H6166", "H6168", "H6170", "H6172",
        "H6175", "H6176", "H6177", "H6178", "H6179",
        # --- H618x-H619x: LED strips ---
        "H6181", "H6182", "H6188", "H6189",
        # --- H619x: misc ---
        "H6195", "H6198",
        # --- H70xx: ceiling / panel lights ---
        "H7000", "H7001", "H7002", "H7003", "H7004", "H7005", "H7006",
        # --- H701x-H702x: LED strips ---
        "H7010", "H7011", "H7012", "H7013", "H7014", "H7015",
        "H7016", "H7017", "H7018", "H7019",
        "H7020", "H7021", "H7022",
        # --- H702x-H703x: LED strips ---
        "H7023", "H7024", "H7025", "H7026", "H7028",
        "H7030", "H7031", "H7032", "H7033", "H7035",
        "H7036", "H7037", "H7038",
        # --- H704x: LED strips ---
        "H7041", "H7042", "H7043", "H7044", "H7045", "H7046", "H7047",
        # --- H705x: LED strips ---
        "H7050", "H7055",
        # --- H706x: LED strips ---
        "H7060", "H7061", "H7062", "H7065",
    }

    def update(self, device: BLEDevice, advertisement: AdvertisementData) -> None:
        """Update device data from advertisement (lights carry no sensor data)."""
        self.update_device(device)

    def dict(self):
        """Return pertinent data about this device."""
        return {
            "address": self.address,
            "name": self.name,
            "model": self.model,
        }


VALID_CLASSES: set[Type[Device]] = {H50TH, H507TH, H51TH, H5179, H5183, H5184, GoveeLight}
MODEL_MAP = {model: cls for cls in VALID_CLASSES for model in cls.SUPPORTED_MODELS}


def determine_known_device(
    device: BLEDevice, advertisement: Optional[AdvertisementData] = None
) -> Optional[Device]:
    model = get_govee_model(device.name)
    if model in MODEL_MAP:
        return MODEL_MAP[model](device, advertisement)
    elif model and advertisement and advertisement.manufacturer_data:
        _LOGGER.debug(
            "%s appears to be a Govee %s, but no handler has been created. Consider opening an issue at https://github.com/linkian19/hacs-govee_ble/issues with the advertisement message from above.",
            device.name,
            model,
        )
    return None
