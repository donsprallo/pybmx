# pybmx

This is a Python library for temperature, humidity and air pressure bosch sensor
devices like the BME280.

## Installation

```bash
python -m pip install pybmx
```

## Usage

```python
import time
import pybmx
import smbus2 as smbus

# Create a new BME280 object. The current sensor configuration is
# read from the sensor and can be printed.
bus = smbus.SMBus(1)
bme = pybmx.Bme280(bus)
bme.info()

# Configure the BME280 sensor. To enable all sensor functions, the
# oversampling must be activated.
bme.temperature_oversampling = pybmx.Bme280Oversampling.OVERSAMPLING_X1
bme.humidity_oversampling = pybmx.Bme280Oversampling.OVERSAMPLING_X1
bme.pressure_oversampling = pybmx.Bme280Oversampling.OVERSAMPLING_X1

# After the configuration, the sensor must be updated to apply the
# new settings.
bme.update()
bme.info()

try:
    while True:
        # You can read the sensor data with the measure() method. The
        # data contains the temperature, humidity and pressure values.
        datapoint = bme.measure()
        print(f"timestamp: {datapoint.timestamp}")
        print(f"temperature: {datapoint.temperature} °C")
        print(f"humidity: {datapoint.humidity} %")
        print(f"pressure: {datapoint.pressure} hPa")

        time.sleep(5.0)
except KeyboardInterrupt:
    pass
finally:
    bus.close()
```
