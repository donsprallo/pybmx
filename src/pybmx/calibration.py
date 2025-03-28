import abc
import ctypes

CALIB_LOW_SIZE = 25
CALIB_HIGH_SIZE = 7


class Bme280CalibrationRegisterMap(ctypes.Structure):
    _fields_ = [
        # Read only: 0x88 ... 0xA1
        ("calib_low", ctypes.c_ubyte * CALIB_LOW_SIZE),
        # Read only: 0xE1 ... 0xF9
        ("calib_high", ctypes.c_ubyte * CALIB_HIGH_SIZE),
    ]

    @property
    def dig_T1(self) -> int:
        data = bytes(self.calib_low[0:2])
        return int.from_bytes(data, "little")

    @property
    def dig_T2(self) -> int:
        data = bytes(self.calib_low[2:4])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_T3(self) -> int:
        data = bytes(self.calib_low[4:6])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P1(self) -> int:
        data = bytes(self.calib_low[6:8])
        return int.from_bytes(data, "little")

    @property
    def dig_P2(self) -> int:
        data = bytes(self.calib_low[8:10])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P3(self) -> int:
        data = bytes(self.calib_low[10:12])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P4(self) -> int:
        data = bytes(self.calib_low[12:14])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P5(self) -> int:
        data = bytes(self.calib_low[14:16])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P6(self) -> int:
        data = bytes(self.calib_low[16:18])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P7(self) -> int:
        data = bytes(self.calib_low[18:20])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P8(self) -> int:
        data = bytes(self.calib_low[20:22])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_P9(self) -> int:
        data = bytes(self.calib_low[22:24])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_H1(self) -> int:
        data = bytes(self.calib_low[24])
        return int.from_bytes(data)

    @property
    def dig_H2(self) -> int:
        data = bytes(self.calib_high[0:2])
        return int.from_bytes(data, "little", signed=True)

    @property
    def dig_H3(self) -> int:
        data = bytes(self.calib_high[2])
        return int.from_bytes(data)

    @property
    def dig_H4(self) -> int:
        hi_nibble = self.calib_high[3] << 4
        lo_nibble = self.calib_high[4] & 0x0F
        return int(lo_nibble | hi_nibble)

    @property
    def dig_H5(self) -> int:
        lo_nibble = (self.calib_high[4] & 0xF0) >> 4
        hi_nibble = self.calib_high[5] << 4
        return int(lo_nibble | hi_nibble)

    @property
    def dig_H6(self) -> int:
        data = bytes(self.calib_high[6])
        return int.from_bytes(data, signed=True)


class Bme280Calibrator(abc.ABC):

    def __init__(self, calibration: Bme280CalibrationRegisterMap):
        self._calibration = calibration

    @abc.abstractmethod
    def temperature(self, adc: int) -> tuple[float, float]:
        raise NotImplementedError

    @abc.abstractmethod
    def pressure(self, adc: int, fine: float) -> float:
        raise NotImplementedError

    @abc.abstractmethod
    def humidity(self, adc: int, fine: float) -> float:
        raise NotImplementedError


class Bme280S32Calibrator(Bme280Calibrator):

    def temperature(self, adc: int) -> tuple[float, float]:
        dig_T1 = self._calibration.dig_T1
        dig_T2 = self._calibration.dig_T2
        dig_T3 = self._calibration.dig_T3

        var1 = (adc >> 3) - (dig_T1 << 1)
        var2 = dig_T2 >> 11
        var3 = (adc >> 4) - dig_T1
        var4 = (adc >> 4) - (dig_T3 >> 12)
        var5 = dig_T3 >> 14
        fine = (var1 * var2) + (var3 * var4 * var5)
        return fine, ((fine * 5 + 128) >> 8) / 100.0

    def pressure(self, adc: int, fine: float) -> float:
        dig_P1 = self._calibration.dig_P1
        dig_P2 = self._calibration.dig_P2
        dig_P3 = self._calibration.dig_P3
        dig_P4 = self._calibration.dig_P4
        dig_P5 = self._calibration.dig_P5
        dig_P6 = self._calibration.dig_P6
        dig_P7 = self._calibration.dig_P7
        dig_P8 = self._calibration.dig_P8
        dig_P9 = self._calibration.dig_P9

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

    def humidity(self, adc: int, fine: float) -> float:
        dig_H1 = self._calibration.dig_H1
        dig_H2 = self._calibration.dig_H2
        dig_H3 = self._calibration.dig_H3
        dig_H4 = self._calibration.dig_H4
        dig_H5 = self._calibration.dig_H5
        dig_H6 = self._calibration.dig_H6

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


class Bme280FloatCalibrator(Bme280Calibrator):

    def temperature(self, adc: int) -> tuple[float, float]:
        adc = float(adc)

        dig_T1 = self._calibration.dig_T1
        dig_T2 = self._calibration.dig_T2
        dig_T3 = self._calibration.dig_T3

        var2 = adc / 131072.0
        var4 = dig_T1 / 8192.0

        var5 = (adc / 16384.0 - dig_T1 / 1024.0) * dig_T2
        var6 = (var2 - var4) * (var2 - var4) * dig_T3

        fine = int(var5 + var6)
        temp = (var5 + var6) / 5120.0
        return fine, temp

    def pressure(self, adc: int, fine: float) -> float:
        adc = float(adc)

        dig_P1 = self._calibration.dig_P1
        dig_P2 = self._calibration.dig_P2
        dig_P3 = self._calibration.dig_P3
        dig_P4 = self._calibration.dig_P4
        dig_P5 = self._calibration.dig_P5
        dig_P6 = self._calibration.dig_P6
        dig_P7 = self._calibration.dig_P7
        dig_P8 = self._calibration.dig_P8
        dig_P9 = self._calibration.dig_P9

        var1 = (fine / 2) - 64000
        var2 = var1 * var1 * dig_P6 / 32768
        var2 += (var1 * dig_P5 * 2) / 4
        var2 += dig_P4 * 65536
        var3 = dig_P3 * var1 * var1 / 524288
        var1 = (var3 + (dig_P2 * var1)) / 524288
        var1 = (1 + var1 / 32768) * dig_P1
        if var1 == 0:
            return 0.0
        p = 1048576 - adc
        p = p - (var2 / 4096) * 6250 / var1
        var1 = dig_P9 * p * p / 2147483648
        var2 = p * dig_P8 / 32768
        p += var1 + var2 + dig_P7

        return p / 16

    def humidity(self, adc: int, fine: float) -> float:
        adc = float(adc)

        dig_H1 = self._calibration.dig_H1
        dig_H2 = self._calibration.dig_H2
        dig_H3 = self._calibration.dig_H3
        dig_H4 = self._calibration.dig_H4
        dig_H5 = self._calibration.dig_H5
        dig_H6 = self._calibration.dig_H6

        var1 = fine - 76800
        x = adc - (dig_H4 * 64 + dig_H5 / 16384 * var1)
        b = 1 + dig_H3 / 67108864 * var1
        z = dig_H2 / 65536 * (1 + dig_H6 / 67108864 * var1 * b)

        var2 = x * z
        var1 = var2 * (1 - dig_H1 * var2 / 524288)

        var1 = min(var1, 100)
        var1 = max(var1, 0)

        return var1
