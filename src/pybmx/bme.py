import ctypes
import datetime
import time
import typing as t
import dataclasses
import smbus2 as smbus

from . import calibration
from . import configuration
from . import enums
from . import utils
from . import io
from . import types
from . import calibration
from . import errors


class Bme280DataRegisterMap(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("_press_msb", ctypes.c_uint8),
        ("_press_lsb", ctypes.c_uint8),
        ("_press_xlsb", ctypes.c_uint8),
        ("_temp_msb", ctypes.c_uint8),
        ("_temp_lsb", ctypes.c_uint8),
        ("_temp_xlsb", ctypes.c_uint8),
        ("_hum_msb", ctypes.c_uint8),
        ("_hum_lsb", ctypes.c_uint8),
    ]

    @property
    def humidity(self) -> types.S32:
        """The raw humidity value"""
        return types.S32(self._hum_msb << 8 | self._hum_lsb)

    @property
    def temperature(self) -> types.S32:
        """The raw temperature value."""
        value = self._temp_xlsb >> 4
        value |= self._temp_lsb << 4
        value |= self._temp_msb << 12
        return types.S32(value & 0xFFFFF)  # 20 bit

    @property
    def pressure(self) -> types.S32:
        """The raw pressure value."""
        value = self._press_xlsb >> 4
        value |= self._press_lsb << 4
        value |= self._press_msb << 12
        return types.S32(value & 0xFFFFF)  # 20 bit


@dataclasses.dataclass(frozen=True)
class BmeDatapoint:
    """BmeDatapoint is a data transfer object for of a single measure. The
    temperature, humidity and pressure is calculated by sensor calibration
    values."""

    timestamp: datetime.datetime
    temperature: float
    humidity: float
    pressure: float


class Bme280:

    DEVICE_ID = 0x60
    """The known device id."""

    DEVICE_ADDRESSES = (0x77, 0x76)
    """Allowed device addresses."""

    TEMPERATURE_RANGE = (-40.0, 85.0)
    """The allowed temperature range in degrees Celsius."""

    # TODO: should be 900 .. 1100 but some sensors report values below 900
    PRESSURE_RANGE = (300.0, 1100.0)
    """The allowed pressure range in hPa."""

    HUMIDITY_RANGE = (10.0, 90.0)
    """The allowed humidity range in %RH."""

    def __init__(
        self,
        bus: smbus.SMBus,
        addr: int = 0x76,
        calibrator_class: t.Type[
            calibration.Bme280Calibrator
        ] = calibration.Bme280FCalibrator,
    ):
        """Create a BME280 sensor class.

        Args:
            bus: The i2c bus interface.
            addr: The device address. Must be 0x76 or 0x77.
            calibrator_class: The class used for calibration calculation.

        Raises:
            ValueError when addr is not 0x76 or 0x77.
        """
        if addr not in self.DEVICE_ADDRESSES:
            raise ValueError("invalid address")

        self._bus = bus
        self._addr = addr
        self._calibrator_class = calibrator_class
        self.reset()

        self._id = self._read_id(self._bus, self._addr)
        if self._id != self.DEVICE_ID:
            raise errors.WrongDeviceError("BME280", self.DEVICE_ID, self._id)

        self._calibration = calibration.read(io.Reader(bus, addr))
        self._config = self._read_config(self._bus, self._addr)

    def reset(self) -> None:
        self._bus.write_byte_data(self._addr, 0xE0, 0xB6)
        time.sleep(0.1)  # wait for device to reset

    def update(self) -> None:
        self._write_config(self._bus, self._addr, self._config)
        self._config = self._read_config(self._bus, self._addr)

    @property
    def addr(self) -> int:
        """Get the device bus address."""
        return self._addr

    @property
    def id(self) -> int:
        """Get the device id."""
        return self._id

    @property
    def mode(self) -> enums.Bme280Mode:
        """Get the current device mode."""
        return self._config.mode

    @mode.setter
    def mode(self, value: enums.Bme280Mode) -> None:
        self._config.mode = value

    @property
    def temperature_oversampling(self) -> enums.Bme280Oversampling:
        return self._config.temperature_oversampling

    @temperature_oversampling.setter
    def temperature_oversampling(self, value: enums.Bme280Oversampling) -> None:
        self._config.temperature_oversampling = value

    @property
    def humidity_oversampling(self) -> enums.Bme280Oversampling:
        return self._config.humidity_oversampling

    @humidity_oversampling.setter
    def humidity_oversampling(self, value: enums.Bme280Oversampling) -> None:
        self._config.humidity_oversampling = value

    @property
    def pressure_oversampling(self) -> enums.Bme280Oversampling:
        return self._config.pressure_oversampling

    @pressure_oversampling.setter
    def pressure_oversampling(self, value: enums.Bme280Oversampling) -> None:
        self._config.pressure_oversampling = value

    @property
    def spi_mode(self) -> bool:
        return self._config.spi_mode

    @spi_mode.setter
    def spi_mode(self, value: bool) -> None:
        self._config.spi_mode = value

    @property
    def filter(self) -> enums.Bme280Filter:
        return self._config.filter

    @filter.setter
    def filter(self, value: enums.Bme280Filter) -> None:
        self._config.filter = value

    @property
    def duration(self) -> enums.Bme280Duration:
        return self._config.duration

    @duration.setter
    def duration(self, value: enums.Bme280Duration) -> None:
        self._config.duration = value

    @staticmethod
    def _write_control_measure(
        bus: smbus.SMBus,
        addr: int,
        osrs_t: enums.Bme280Oversampling,
        osrs_p: enums.Bme280Oversampling,
        mode: enums.Bme280Mode,
    ) -> None:
        """Write 'ctrl_meas' register. This set the temperature and
        pressure oversampling. This also set the device mode."""
        data = 0x0F & mode
        data |= (0x03 | osrs_t) << 5
        data |= (0x03 | osrs_p) << 3
        bus.write_block_data(addr, 0xF4, [data])

    @staticmethod
    def _read_id(bus: smbus.SMBus, addr: int) -> int:
        return io.Reader(bus, addr).read_u8(0xD0).value

    @classmethod
    def _read_config(
        cls, bus: smbus.SMBus, addr: int
    ) -> configuration.Bme280ConfigRegisterMap:
        """Read configuration from device."""
        configmap_size = ctypes.sizeof(configuration.Bme280ConfigRegisterMap)
        buffer = io.Reader(bus, addr).read_bytes(0xF2, configmap_size)
        return configuration.Bme280ConfigRegisterMap.from_buffer(
            bytearray(buffer), 0
        )

    @staticmethod
    def _write_config(
        bus: smbus.SMBus,
        addr: int,
        config: configuration.Bme280ConfigRegisterMap,
    ) -> None:
        # Follow write sequence: must write pairs of register address
        # and value. Note: write to 0xF2 only affects after write to 0xF5.
        write_sequence = bytes(
            utils.gen_write_sequence(config.to_bytes(), addr=0xF2)
        )
        # First byte of write_sequence is the start register address.
        bus.write_i2c_block_data(addr, write_sequence[0], write_sequence[1:])

    @classmethod
    def _read_data(cls, bus: smbus.SMBus, addr: int) -> Bme280DataRegisterMap:
        """Read data from device."""
        register_map_size = ctypes.sizeof(Bme280DataRegisterMap)
        buffer = io.Reader(bus, addr).read_bytes(0xF7, register_map_size)
        return Bme280DataRegisterMap.from_buffer(bytearray(buffer), 0)

    @staticmethod
    def _sleep(duration: enums.Bme280Duration) -> None:
        match duration:
            case enums.Bme280Duration.DURATION_0P5:
                time.sleep(0.005)
            case enums.Bme280Duration.DURATION_10:
                time.sleep(0.01)
            case enums.Bme280Duration.DURATION_20:
                time.sleep(0.02)
            case enums.Bme280Duration.DURATION_62P5:
                time.sleep(0.0625)
            case enums.Bme280Duration.DURATION_125:
                time.sleep(0.125)
            case enums.Bme280Duration.DURATION_250:
                time.sleep(0.250)
            case enums.Bme280Duration.DURATION_500:
                time.sleep(0.5)
            case enums.Bme280Duration.DURATION_1000:
                time.sleep(1.0)

    def measure(self) -> BmeDatapoint:
        # Create timestamp here, because we trigger conversion as soon
        # as possible. The read data is buffered until next conversion
        # is started.
        now = datetime.datetime.now()
        # Trigger a single conversion by set up force mode. After the
        # conversion, the sensor go back to sleep mode.
        self._config.mode = enums.Bme280Mode.FORCED
        self._write_config(self._bus, self._addr, self._config)
        self._sleep(self._config.duration)
        self._config = self._read_config(self._bus, self._addr)
        if self._config.measuring is True:
            raise TimeoutError("sensor is not ready")
        # Read raw sensor data from device.
        data = self._read_data(self._bus, self._addr)
        # Calculate real values from sensor raw data.
        calibrator = self._calibrator_class(self._calibration)
        temperature = calibrator.temperature(data.temperature)
        pressure = calibrator.pressure(data.pressure)
        humidity = calibrator.humidity(data.humidity)
        # Validate the calculated values.
        if not utils.in_range(temperature, self.TEMPERATURE_RANGE):
            raise errors.ImplausibleDataError(
                temperature, self.TEMPERATURE_RANGE
            )
        if not utils.in_range(pressure, self.PRESSURE_RANGE):
            raise errors.ImplausibleDataError(pressure, self.PRESSURE_RANGE)
        if not utils.in_range(humidity, self.HUMIDITY_RANGE):
            raise errors.ImplausibleDataError(humidity, self.HUMIDITY_RANGE)
        # Return data transfer object with timestamp and
        # previously calculated real data.
        return BmeDatapoint(
            timestamp=now,
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
        )

    def info(self, writer=print) -> None:
        writer(f"-----------------------")
        writer(f"      id: {hex(self.id)}")
        writer(f"    addr: {hex(self.addr)}")
        writer(f"  osrs_h: {self.humidity_oversampling.name}")
        writer(f"  osrs_t: {self.temperature_oversampling.name}")
        writer(f"  osrs_p: {self.pressure_oversampling.name}")
        writer(f"     spi: {self.spi_mode}")
        writer(f"  filter: {self.filter.name}")
        writer(f"duration: {self.duration.name}")
