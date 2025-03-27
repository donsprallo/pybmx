import typing as t


def chunk_iterator(size: int, chunk_size: int):
    chunk_start = 0
    while size > 0:
        chunk_length = min(size, chunk_size)
        yield chunk_start, chunk_length
        chunk_start += chunk_length
        size -= chunk_length


def gen_write_sequence(data: bytes, addr: int) -> t.Generator[int, None, None]:
    """Generate a write byte sequence for a bme sensor."""
    for byte in data:
        yield addr
        yield byte
        addr += 1


def hex_dump(data: bytes | bytearray, width: int = 16, addr: int = 0) -> str:
    """Print a readable hex table of a bytes or bytearray object.

    Args:
        data: The input data as `bytes` or `bytearray`.
        width: The number of bytes per line (default: 16).
        addr: The starting address (default: 0).

    Returns:
        A string representing the hex table.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("Invalid type")

    header = "Offset    " + " ".join(f"{i:02X}" for i in range(width)) + "  |ASCII|"
    lines = [header, "-" * len(header)]

    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_bytes = " ".join(f"{byte:02X}" for byte in chunk)
        hex_bytes = hex_bytes.ljust(width * 3)
        ascii_repr = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        lines.append(f"{addr + offset:08X}  {hex_bytes} |{ascii_repr}|")
    return "\n".join(lines)
