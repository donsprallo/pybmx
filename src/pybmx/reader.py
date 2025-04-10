import smbus2 as smbus
from . import types


class Reader:
    """Wrap an I2C bus instance to provide a common interface for
    reading from the bus."""

    def __init__(self, bus: smbus.SMBus, address: int):
        self._bus = bus
        self._address = address

    def read_u16(self, register: int) -> types.U16:
        """Read a 16-bit unsigned integer from the bus."""
        data = self._bus.read_word_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#06x}")
        return types.U16(data)

    def read_s16(self, register: int) -> types.S16:
        """Read a 16-bit signed integer from the bus."""
        data = self._bus.read_word_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#06x}")
        return types.S16(data)

    def read_u8(self, register: int) -> types.U8:
        """Read an 8-bit unsigned integer from the bus."""
        data = self._bus.read_byte_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#04x}")
        return types.U8(data)

    def read_s8(self, register: int) -> types.S8:
        """Read an 8-bit signed integer from the bus."""
        data = self._bus.read_byte_data(self._address, register)
        print(f"Register: {register:#04x}, Data: {data:#04x}")
        return types.S8(data)
