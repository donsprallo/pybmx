import ctypes
import datetime
import time
import typing as t

import pydantic
import smbus2 as smbus

from . import calibration
from . import configuration
from . import enums
from . import utils

I2C_SMBUS_BLOCK_MAX = 32
"""Maximum size of readable data bytes per read."""

BME280_DEVICE_ID = 0x60
"""The known device id."""

BME280_DEVICE_ADDRESSES = (0x77, 0x76)
"""Allowed device addresses."""


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
    def humidity(self) -> int:
        """The raw humidity value"""
        return self._hum_msb << 8 | self._hum_lsb

    @property
    def temperature(self) -> int:
        """The raw temperature value."""
        value = self._temp_xlsb >> 4
        value |= self._temp_lsb << 4
        value |= self._temp_msb << 12
        return value & 0xFFFFF  # 20 bit

    @property
    def pressure(self) -> int:
        """The raw pressure value."""
        value = self._press_xlsb >> 4
        value |= self._press_lsb << 4
        value |= self._press_msb << 12
        return value & 0xFFFFF  # 20 bit


class BmeDatapoint(pydantic.BaseModel):
    """BmeDatapoint is a data transfer object for of a single measure. The
    temperature, humidity and pressure is calculated by sensor calibration
    values."""

    timestamp: datetime.datetime
    temperature: float
    humidity: float
    pressure: float


class Bme280:

    def __init__(
        self,
        bus: smbus.SMBus,
        addr: int = 0x76,
        calibrator_class: t.Type[
            calibration.Bme280Calibrator
        ] = calibration.Bme280S32Calibrator,
    ):
        """Create a BME280 sensor class.

        Args:
            bus: The i2c bus interface.
            addr: The device address. Must be 0x76 or 0x77.
            calibrator_class: The class used for calibration calculation.

        Raises:
            ValueError when addr is not 0x76 or 0x77.
        """
        if addr not in BME280_DEVICE_ADDRESSES:
            raise ValueError("invalid address")

        self._bus = bus
        self._addr = addr
        self._calibrator_class = calibrator_class
        self.reset()

        self._id = self._read_id(self._bus, self._addr)
        if self._id != BME280_DEVICE_ID:
            raise ValueError("unknown device")

        self._calibration = self._read_calibration(self._bus, self._addr)
        self._config = self._read_config(self._bus, self._addr)

    def reset(self) -> None:
        self._bus.write_byte_data(self._addr, 0xE0, 0xB6)

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
        return int.from_bytes(bus.read_i2c_block_data(addr, 0xD0, 1))

    @classmethod
    def _read_calibration(
        cls, bus: smbus.SMBus, addr: int
    ) -> calibration.Bme280CalibrationRegisterMap:
        """Read calibration from device."""
        buffer = bytearray()
        low_map_size = calibration.CALIB_LOW_SIZE
        high_map_size = calibration.CALIB_HIGH_SIZE
        buffer.extend(cls._read_block_data(bus, addr, 0x88, low_map_size))
        buffer.extend(cls._read_block_data(bus, addr, 0xE1, high_map_size))
        return calibration.Bme280CalibrationRegisterMap.from_buffer(buffer, 0)

    @classmethod
    def _read_config(
        cls, bus: smbus.SMBus, addr: int
    ) -> configuration.Bme280ConfigRegisterMap:
        """Read configuration from device."""
        configmap_size = ctypes.sizeof(configuration.Bme280ConfigRegisterMap)
        buffer = cls._read_block_data(bus, addr, 0xF2, configmap_size)
        return configuration.Bme280ConfigRegisterMap.from_buffer(buffer, 0)

    @staticmethod
    def _write_config(
        bus: smbus.SMBus, addr: int, config: configuration.Bme280ConfigRegisterMap
    ) -> None:
        # Follow write sequence: must write pairs of register address
        # and value. Note: write to 0xF2 only affects after write to 0xF5.
        write_sequence = bytes(utils.gen_write_sequence(config.to_bytes(), addr=0xF2))
        # First byte of write_sequence is the start register address.
        bus.write_i2c_block_data(addr, write_sequence[0], write_sequence[1:])

    @classmethod
    def _read_data(cls, bus: smbus.SMBus, addr: int) -> Bme280DataRegisterMap:
        """Read data from device."""
        register_map_size = ctypes.sizeof(Bme280DataRegisterMap)
        buffer = cls._read_block_data(bus, addr, 0xF7, register_map_size)
        return Bme280DataRegisterMap.from_buffer(buffer, 0)

    @staticmethod
    def _read_block_data(
        bus: smbus.SMBus, addr: int, register: int, length: int
    ) -> bytearray:
        # TODO: read chunks and add to buffer.
        buffer = bytearray()
        iterator = utils.chunk_iterator(length, I2C_SMBUS_BLOCK_MAX)
        for chunk_start, chunk_size in iterator:
            register_addr = register + chunk_start
            data_block = bus.read_i2c_block_data(addr, register_addr, chunk_size)
            buffer.extend(data_block)
        # print(utils.hex_dump(buffer, width=16, addr=register))
        return buffer

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
        fine, temperature = calibrator.temperature(data.temperature)
        pressure = calibrator.pressure(data.pressure, fine)
        humidity = calibrator.humidity(data.humidity, fine)
        # Return data transfer object with timestamp and
        # previously calculated real data.
        return BmeDatapoint(
            timestamp=now, temperature=temperature, humidity=humidity, pressure=pressure
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
