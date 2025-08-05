import typing as t


class PyBmxError(Exception):
    """Base class for all PyBMX exceptions."""

    pass


class WrongDeviceError(PyBmxError):
    """Exception raised when the device has not valid ID."""

    def __init__(self, device: str, expected_id: int, actual_id: int):
        super().__init__(f"device {device} has not valid ID")
        self.device = device
        self.expected_id = expected_id
        self.actual_id = actual_id

    def __str__(self):
        return "device {} has not valid ID (expected: {}, actual: {})".format(
            self.device, self.expected_id, self.actual_id
        )


class ImplausibleDataError(PyBmxError):
    """Exception raised when the data is implausible."""

    def __init__(self, value: float, values: t.Tuple[float, float]):
        super().__init__(
            f"data {value} is implausible ({values[0]}, {values[1]})"
        )
