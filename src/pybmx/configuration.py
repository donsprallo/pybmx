import ctypes

from . import enums


class Bme280ConfigRegisterMap(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        # Read / write: 0xF2
        ("_ctrl_hum", ctypes.c_uint8),
        # Read only: 0xF3
        ("_status", ctypes.c_uint8),
        # Read / write: 0xF4
        ("_ctrl_meas", ctypes.c_uint8),
        # Read / write: 0xF5
        ("_config", ctypes.c_uint8),
    ]

    @property
    def mode(self) -> enums.Bme280Mode:
        # Get ctrl_meas.bits[1:0]
        value = self._ctrl_meas & 0x03
        # TODO: can be FORCED_MODE
        return enums.Bme280Mode(value)

    @mode.setter
    def mode(self, value: enums.Bme280Mode) -> None:
        # Set ctrl_meas.bits[1:0]
        self._ctrl_meas &= ~0x03
        self._ctrl_meas |= value & 0x03

    @property
    def humidity_oversampling(self) -> enums.Bme280Oversampling:
        # Get ctrl_hum.bits[2:0]
        value = self._ctrl_hum & 0x07
        # TODO: can be OVERSAMPLING_X16
        return enums.Bme280Oversampling(value)

    @humidity_oversampling.setter
    def humidity_oversampling(self, value: enums.Bme280Oversampling) -> None:
        # Set ctrl_hum.bits[2:0]
        self._ctrl_hum &= ~0x07
        self._ctrl_hum |= value & 0x07

    @property
    def temperature_oversampling(self) -> enums.Bme280Oversampling:
        # Get ctrl_meas.bits[7:5]
        value = (self._ctrl_meas >> 5) & 0x07
        # TODO: can be OVERSAMPLING_X16
        return enums.Bme280Oversampling(value)

    @temperature_oversampling.setter
    def temperature_oversampling(self, value: enums.Bme280Oversampling) -> None:
        # Set ctrl_meas.bits[7:5]
        self._ctrl_meas &= ~(0x07 << 5)
        self._ctrl_meas |= (value & 0x07) << 5

    @property
    def pressure_oversampling(self) -> enums.Bme280Oversampling:
        # Get ctrl_meas.bits[4:2]
        value = (self._ctrl_meas >> 2) & 0x07
        # TODO: can be OVERSAMPLING_X16
        return enums.Bme280Oversampling(value)

    @pressure_oversampling.setter
    def pressure_oversampling(self, value: enums.Bme280Oversampling) -> None:
        # Set ctrl_meas.bits[4:2]
        self._ctrl_meas &= ~(0x07 << 2)
        self._ctrl_meas |= (value & 0x07) << 2

    @property
    def duration(self) -> enums.Bme280Duration:
        # Get config.bits[7:5]
        value = (self._config >> 5) & 0x03
        return enums.Bme280Duration(value)

    @duration.setter
    def duration(self, value: enums.Bme280Duration) -> None:
        # Set config.bits[7:5]
        self._config &= ~(0x07 << 5)
        self._config |= (value & 0x07) << 5

    @property
    def filter(self) -> enums.Bme280Filter:
        # Get config.bits[4:2]
        value = (self._config >> 2) & 0x07
        return enums.Bme280Filter(value)

    @filter.setter
    def filter(self, value: enums.Bme280Filter) -> None:
        # Set config.bits[4:2]
        self._config &= ~(0x07 << 2)
        self._config |= (value & 0x07) << 2

    @property
    def spi_mode(self) -> bool:
        # Get config.bits[0]
        return bool(self._config & 0x01)

    @spi_mode.setter
    def spi_mode(self, value: bool) -> None:
        # Set config.bits[0]
        if value is True:
            self._config |= 0x01
        else:
            self._config &= ~0x01

    @property
    def measuring(self) -> bool:
        # Get status.bits[3]
        return bool(self._status & 0x08)

    @property
    def im_update(self) -> bool:
        # Get status.bits[0]
        return bool(self._status & 0x01)

    def to_bytes(self) -> bytes:
        return ctypes.string_at(ctypes.byref(self), ctypes.sizeof(self))
