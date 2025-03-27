import time

import smbus2 as smbus

from . import bme
from . import calibration
from . import enums

if __name__ == "__main__":
    bus = smbus.SMBus(1)
    calibrator = calibration.Bme280FloatCalibrator
    # calibrator = calibration.Bme280S32Calibrator
    bme = bme.Bme280(bus, calibrator_class=calibrator)
    bme.info()

    bme.duration = enums.Bme280Duration.DURATION_250
    bme.temperature_oversampling = enums.Bme280Oversampling.OVERSAMPLING_X1
    bme.humidity_oversampling = enums.Bme280Oversampling.OVERSAMPLING_X1
    bme.pressure_oversampling = enums.Bme280Oversampling.OVERSAMPLING_X1
    bme.update()
    bme.info()

    try:
        while True:
            datapoint = bme.measure()
            print(datapoint)
            time.sleep(5.0)
    except KeyboardInterrupt:
        pass
    bus.close()
