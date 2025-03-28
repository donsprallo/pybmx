import enum


class Bme280Mode(enum.IntFlag):
    """The BME280 power mode.

    The sensor offers three modes:

    - Sleep mode: The sensor is in sleep mode and no measurements are
      performed. All registers are accessible. The sensor is in low power
      mode. This mode is selected by default after power on.
    - Forced mode: Perform a single measurement. Store the result in the
      sensor registers and go back to sleep mode.
    - Normal mode: The sensor is in normal mode. It performs cycles of
      continuous measurements and inactive periods.
    """

    SLEEP = 0
    FORCED = 1
    NORMAL = 3


class Bme280Oversampling(enum.IntFlag):
    SKIPPED = 0x00
    OVERSAMPLING_X1 = 0x01
    OVERSAMPLING_X2 = 0x02
    OVERSAMPLING_X4 = 0x03
    OVERSAMPLING_X8 = 0x04
    OVERSAMPLING_X16 = 0x05


class Bme280Duration(enum.IntFlag):
    """The inactive duration in normal mode. Time code
    is in milliseconds."""

    DURATION_0P5 = 0x00
    DURATION_62P5 = 0x01
    DURATION_125 = 0x02
    DURATION_250 = 0x03
    DURATION_500 = 0x04
    DURATION_1000 = 0x05
    DURATION_10 = 0x06
    DURATION_20 = 0x07


class Bme280Filter(enum.IntFlag):
    FILTER_OFF = 0x00
    FILTER_2 = 0x01
    FILTER_4 = 0x02
    FILTER_8 = 0x03
    FILTER_16 = 0x04
