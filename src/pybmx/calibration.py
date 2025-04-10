import abc
import ctypes
import typing as t
import smbus2 as smbus
import dataclasses

U8: t.TypeAlias = ctypes.c_uint8
S8: t.TypeAlias = ctypes.c_int8
S16: t.TypeAlias = ctypes.c_int16
U16: t.TypeAlias = ctypes.c_uint16
S32: t.TypeAlias = ctypes.c_int32
U32: t.TypeAlias = ctypes.c_uint32


class Reader:
    """Wrap an I2C bus instance to provide a common interface for
    reading from the bus."""

    def __init__(self, bus: smbus.SMBus, address: int):
        self._bus = bus
        self._address = address

    def u16(self, register: int) -> U16:
        """Read a 16-bit unsigned integer from the bus."""
        data = self._bus.read_word_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#06x}")
        return U16(data)

    def s16(self, register: int) -> S16:
        """Read a 16-bit signed integer from the bus."""
        data = self._bus.read_word_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#06x}")
        return S16(data)

    def u8(self, register: int) -> U8:
        """Read an 8-bit unsigned integer from the bus."""
        data = self._bus.read_byte_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#04x}")
        return U8(data)

    def s8(self, register: int) -> S8:
        """Read an 8-bit signed integer from the bus."""
        data = self._bus.read_byte_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#04x}")
        return S8(data)


@dataclasses.dataclass
class Bme280Calibration:
    dig_T1: U16
    dig_T2: S16
    dig_T3: S16
    dig_P1: U16
    dig_P2: S16
    dig_P3: S16
    dig_P4: S16
    dig_P5: S16
    dig_P6: S16
    dig_P7: S16
    dig_P8: S16
    dig_P9: S16
    dig_H1: U8
    dig_H2: S16
    dig_H3: U8
    dig_H4: S16
    dig_H5: S16
    dig_H6: S8


class Bme280Calibrator(abc.ABC):

    def __init__(self, calibration: Bme280Calibration):
        self._calibration = calibration

    @abc.abstractmethod
    def fine(self, adc: S32) -> float:
        """Get the fine temperature value."""
        raise NotImplementedError

    @abc.abstractmethod
    def temperature(self, adc: S32) -> float:
        raise NotImplementedError

    @abc.abstractmethod
    def pressure(self, adc: S32, fine: S32) -> float:
        raise NotImplementedError

    @abc.abstractmethod
    def humidity(self, adc: S32, fine: S32) -> float:
        raise NotImplementedError


class Bme280S32Calibrator(Bme280Calibrator):

    def temperature(self, adc: S32) -> float:
        fine = self.fine(adc).value
        adc_val = adc.value

        dig_T1 = self._calibration.dig_T1.value
        dig_T2 = self._calibration.dig_T2.value
        dig_T3 = self._calibration.dig_T3.value

        var1 = (adc_val >> 4) - dig_T1
        var2 = ((((adc_val >> 3) - (dig_T1 << 1))) * dig_T2) >> 11
        var3 = (((var1 * var1) >> 12) * dig_T3) >> 14

        fine = var2 + var3
        return fine, ((fine * 5 + 128) >> 8) / 100.0

    def pressure(self, adc: S32) -> float:
        fine = self.fine(adc).value
        adc = adc.value

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
        p = 1048576 - adc
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (dig_P9 * ((p >> 13) ** 2)) >> 25
        var2 = (dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (dig_P7 << 4)
        # Convert Q24.8 to float.
        return p / 256

    def humidity(self, adc: S32) -> float:
        fine = self.fine(adc).value
        adc = adc.value

        dig_H1 = self._calibration.dig_H1.value
        dig_H2 = self._calibration.dig_H2.value
        dig_H3 = self._calibration.dig_H3.value
        dig_H4 = self._calibration.dig_H4.value
        dig_H5 = self._calibration.dig_H5.value
        dig_H6 = self._calibration.dig_H6.value

        v_x1_u32r = fine - 76800

        var1 = (adc << 14) - (dig_H4 << 20) - (dig_H5 * v_x1_u32r)
        var2 = (var1 + 16384) >> 15
        var3 = (v_x1_u32r * dig_H6) >> 10
        var4 = ((v_x1_u32r * dig_H3) >> 11) + 32768
        var5 = ((var3 * var4) >> 10) + 2097152
        var6 = (var5 * dig_H2 + 8192) >> 14
        v_x1_u32r = var2 * var6

        var7 = ((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7
        v_x1_u32r -= var7 * (dig_H1 >> 4)

        v_x1_u32r = max(v_x1_u32r, 0)
        v_x1_u32r = min(v_x1_u32r, 419430400)
        # Convert Q22.10 to float.
        return (v_x1_u32r >> 12) / 1024


class Bme280FCalibrator(Bme280Calibrator):

    def fine(self, adc: S32) -> float:
        adc = float(adc.value)

        dig_T1 = self._calibration.dig_T1.value
        dig_T2 = self._calibration.dig_T2.value
        dig_T3 = self._calibration.dig_T3.value

        var1 = (adc / 16384.0 - dig_T1 / 1024.0) * dig_T2
        var2 = ((adc / 131072.0 - dig_T1 / 8192.0) ** 2) * dig_T3

        return var1 + var2

    def temperature(self, adc: S32) -> float:
        fine = self.fine(adc)
        return fine / 5120.0

    def pressure(self, adc: S32) -> float:
        fine = self.fine(adc)
        adc = float(adc.value)

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

        if var1 == 0:
            return 0.0

        p = 1048576.0 - adc
        p = ((p - var2 / 4096.0)) * 6250.0 / var1
        var1 = dig_P9 * p * p / 2147483648.0
        var2 = p * dig_P8 / 32768.0
        p = p + (var1 + var2 + dig_P7) / 16.0
        return p / 100.0

    def humidity(self, adc: S32) -> float:
        fine = self.fine(adc)
        adc = float(adc.value)

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
        var1 = (adc - var2) * (dig_H2 / 65536.0 * var4)
        var1 = var1 * (1.0 - (dig_H1 * var1 / 524288.0))

        return max(0.0, min(var1, 100.0))
