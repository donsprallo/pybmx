import abc
import dataclasses

from . import types
from . import io


@dataclasses.dataclass(frozen=True)
class Bme280Calibration:
    """A dataclass to hold the calibration data for the BME280 sensor."""

    dig_T1: types.U16
    dig_T2: types.S16
    dig_T3: types.S16
    dig_P1: types.U16
    dig_P2: types.S16
    dig_P3: types.S16
    dig_P4: types.S16
    dig_P5: types.S16
    dig_P6: types.S16
    dig_P7: types.S16
    dig_P8: types.S16
    dig_P9: types.S16
    dig_H1: types.U8
    dig_H2: types.S16
    dig_H3: types.U8
    dig_H4: types.S16
    dig_H5: types.S16
    dig_H6: types.S8


def read(reader: io.Reader) -> Bme280Calibration:
    """Read calibration from data from reader."""
    e4 = reader.read_s8(0xE4).value
    e5 = reader.read_s8(0xE5).value
    e6 = reader.read_s8(0xE6).value
    return Bme280Calibration(
        # Read temperature calibration values.
        dig_T1=reader.read_u16(0x88),
        dig_T2=reader.read_s16(0x8A),
        dig_T3=reader.read_s16(0x8C),
        # Read pressure calibration values.
        dig_P1=reader.read_u16(0x8E),
        dig_P2=reader.read_s16(0x90),
        dig_P3=reader.read_s16(0x92),
        dig_P4=reader.read_s16(0x94),
        dig_P5=reader.read_s16(0x96),
        dig_P6=reader.read_s16(0x98),
        dig_P7=reader.read_s16(0x9A),
        dig_P8=reader.read_s16(0x9C),
        dig_P9=reader.read_s16(0x9E),
        # Read humidity calibration values.
        dig_H1=reader.read_u8(0xA1),
        dig_H2=reader.read_s16(0xE1),
        dig_H3=reader.read_u8(0xE3),
        dig_H4=types.S16((e4 << 4) | (e5 & 0x0F)),
        dig_H5=types.S16((e6 << 4) | (e5 >> 4)),
        dig_H6=reader.read_s8(0xE7),
    )


class Bme280Calibrator(abc.ABC):
    """Base class for BME280 calibrators. This class defines the
    interface for the calibration calculation."""

    def __init__(self, calibration: Bme280Calibration):
        """Create a new BME280 calibrator.

        Args:
            calibration: The calibration data for the BME280 sensor.
        """
        self._calibration = calibration

    @abc.abstractmethod
    def fine(self, adc: types.S32) -> float:
        """Get the fine compensation value."""
        raise NotImplementedError

    @abc.abstractmethod
    def temperature(self, adc: types.S32) -> float:
        """Get the compensated temperature value.

        Args:
            adc: The raw ADC value for temperature.

        Returns:
            The temperature value in degrees Celsius.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pressure(self, adc: types.S32) -> float:
        """Get the compensated pressure value.

        Args:
            adc: The raw ADC value for pressure.

        Returns:
            The pressure value in hPa.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def humidity(self, adc: types.S32) -> float:
        """Get the compensated humidity value.

        Args:
            adc: The raw ADC value for humidity.

        Returns:
            The humidity value in %RH.
        """
        raise NotImplementedError


class Bme280S32Calibrator(Bme280Calibrator):
    """The BME280 calibrator for 32-bit signed integers. This class
    implements the calibration calculations using 32-bit signed
    integers for the ADC values."""

    def fine(self, adc: types.S32) -> float:
        _adc = adc.value

        dig_T1 = self._calibration.dig_T1.value
        dig_T2 = self._calibration.dig_T2.value
        dig_T3 = self._calibration.dig_T3.value

        var1 = (_adc >> 4) - dig_T1
        var2 = ((((_adc >> 3) - (dig_T1 << 1))) * dig_T2) >> 11
        var3 = (((var1 * var1) >> 12) * dig_T3) >> 14

        return var2 + var3

    def temperature(self, adc: types.S32) -> float:
        fine = types.S32(int(self.fine(adc))).value
        return ((fine * 5 + 128) >> 8) / 100.0

    def pressure(self, adc: types.S32) -> float:
        fine = types.S32(int(self.fine(adc))).value
        _adc = adc.value

        dig_P1 = self._calibration.dig_P1.value
        dig_P2 = self._calibration.dig_P2.value
        dig_P3 = self._calibration.dig_P3.value
        dig_P4 = self._calibration.dig_P4.value
        dig_P5 = self._calibration.dig_P5.value
        dig_P6 = self._calibration.dig_P6.value
        dig_P7 = self._calibration.dig_P7.value
        dig_P8 = self._calibration.dig_P8.value
        dig_P9 = self._calibration.dig_P9.value

        var1 = fine - 128000
        var2 = var1 * var1 * dig_P6
        var2 += var1 * (dig_P5 << 17)
        var2 += dig_P4 << 35
        var3 = var1 * var1 * (dig_P3 >> 8)
        var4 = var1 * (dig_P2 << 12)
        var1 = var3 + var4
        var1 = ((1 << 47) + var1) * dig_P1 >> 33

        # Avoid division by zero.
        if var1 == 0:
            return 0.0

        p = 1048576 - _adc
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (dig_P9 * ((p >> 13) ** 2)) >> 25
        var2 = (dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (dig_P7 << 4)
        # Convert Q24.8 to float.
        p = p / 265
        return p / 100.0

    def humidity(self, adc: types.S32) -> float:
        fine = types.S32(int(self.fine(adc))).value
        _adc = adc.value

        dig_H1 = self._calibration.dig_H1.value
        dig_H2 = self._calibration.dig_H2.value
        dig_H3 = self._calibration.dig_H3.value
        dig_H4 = self._calibration.dig_H4.value
        dig_H5 = self._calibration.dig_H5.value
        dig_H6 = self._calibration.dig_H6.value

        v_x1_u32r = fine - 76800

        var1 = (_adc << 14) - (dig_H4 << 20) - (dig_H5 * v_x1_u32r)
        var2 = (var1 + 16384) >> 15
        var3 = (v_x1_u32r * dig_H6) >> 10
        var4 = ((v_x1_u32r * dig_H3) >> 11) + 32768
        var5 = ((var3 * var4) >> 10) + 2097152
        var6 = (var5 * dig_H2 + 8192) >> 14
        v_x1_u32r = var2 * var6

        var7 = ((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7
        v_x1_u32r -= var7 * (dig_H1 >> 4)
        v_x1_u32r = max(0, min(v_x1_u32r, 419430400))

        # Convert Q22.10 to float.
        return (v_x1_u32r >> 12) / 1024


class Bme280FCalibrator(Bme280Calibrator):
    """The BME280 calibrator for 32-bit floating point numbers. This class
    implements the calibration calculations using 32-bit floating point
    numbers for the ADC values."""

    def fine(self, adc: types.S32) -> float:
        _adc = float(adc.value)

        dig_T1 = self._calibration.dig_T1.value
        dig_T2 = self._calibration.dig_T2.value
        dig_T3 = self._calibration.dig_T3.value

        var1 = (_adc / 16384.0 - dig_T1 / 1024.0) * dig_T2
        var2 = ((_adc / 131072.0 - dig_T1 / 8192.0) ** 2) * dig_T3

        return var1 + var2

    def temperature(self, adc: types.S32) -> float:
        fine = self.fine(adc)
        return fine / 5120.0

    def pressure(self, adc: types.S32) -> float:
        fine = self.fine(adc)
        _adc = float(adc.value)

        dig_P1 = self._calibration.dig_P1.value
        dig_P2 = self._calibration.dig_P2.value
        dig_P3 = self._calibration.dig_P3.value
        dig_P4 = self._calibration.dig_P4.value
        dig_P5 = self._calibration.dig_P5.value
        dig_P6 = self._calibration.dig_P6.value
        dig_P7 = self._calibration.dig_P7.value
        dig_P8 = self._calibration.dig_P8.value
        dig_P9 = self._calibration.dig_P9.value

        var1 = (fine / 2.0) - 64000.0
        var2 = var1 * var1 * dig_P6 / 32768.0
        var2 = var2 + var1 * dig_P5 * 2.0
        var2 = var2 / 4.0 + dig_P4 * 65536.0
        var3 = dig_P3 * var1 * var1 / 524288.0
        var1 = (var3 + dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * dig_P1

        # Avoid division by zero.
        if var1 == 0:
            return 0.0

        p = 1048576.0 - _adc
        p = ((p - var2 / 4096.0)) * 6250.0 / var1
        var1 = dig_P9 * p * p / 2147483648.0
        var2 = p * dig_P8 / 32768.0
        p = p + (var1 + var2 + dig_P7) / 16.0
        return p / 100.0

    def humidity(self, adc: types.S32) -> float:
        fine = self.fine(adc)
        _adc = float(adc.value)

        dig_H1 = self._calibration.dig_H1.value
        dig_H2 = self._calibration.dig_H2.value
        dig_H3 = self._calibration.dig_H3.value
        dig_H4 = self._calibration.dig_H4.value
        dig_H5 = self._calibration.dig_H5.value
        dig_H6 = self._calibration.dig_H6.value

        var1 = fine - 76800.0
        var2 = dig_H4 * 64.0 + dig_H5 / 16384.0 * var1
        var3 = 1.0 + dig_H3 / 67108864.0 * var1
        var4 = 1.0 + dig_H6 / 67108864.0 * var1 * var3
        var1 = (_adc - var2) * (dig_H2 / 65536.0 * var4)
        var1 = var1 * (1.0 - (dig_H1 * var1 / 524288.0))

        return max(0.0, min(var1, 100.0))
