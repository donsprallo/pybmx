import smbus2 as smbus
import loguru
from . import types

logger = loguru.logger


class Reader:
    """Wrap an I2C bus instance to provide a common interface for
    reading from the bus."""

    def __init__(self, bus: smbus.SMBus, address: int):
        self._bus = bus
        self._address = address

    def read_u16(self, register: int) -> types.U16:
        """Read a 16-bit unsigned integer from the bus."""
        data = self._bus.read_word_data(self._address, register)
        logger.debug(f"register: {register:#04x}, data: {data:#06x}")
        return types.U16(data)

    def read_s16(self, register: int) -> types.S16:
        """Read a 16-bit signed integer from the bus."""
        data = self._bus.read_word_data(self._address, register)
        logger.debug(f"register: {register:#04x}, data: {data:#06x}")
        return types.S16(data)

    def read_u8(self, register: int) -> types.U8:
        """Read an 8-bit unsigned integer from the bus."""
        data = self._bus.read_byte_data(self._address, register)
        logger.debug(f"register: {register:#04x}, data: {data:#04x}")
        return types.U8(data)

    def read_s8(self, register: int) -> types.S8:
        """Read an 8-bit signed integer from the bus."""
        data = self._bus.read_byte_data(self._address, register)
        logger.debug(f"register: {register:#04x}, data: {data:#04x}")
        return types.S8(data)

    def read_bytes(self, register: int, length: int) -> bytes:
        """Read a number of bytes from the bus."""
        data = self._bus.read_i2c_block_data(self._address, register, length)
        logger.debug(f"register: {register:#04x}, data: {data}")
        return bytes(data)
