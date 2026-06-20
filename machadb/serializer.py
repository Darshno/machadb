"""
serializer.py — The Binary Encoder/Decoder of MachaDB

This module converts Python values into compact binary format
and back again. Think of it as the Google Translate between
Python and raw bytes, but less buggy (hopefully).

Binary Format per value:
    [1 byte: type_tag] [N bytes: payload]

Type tags:
    0x00 = NULL   → 0 bytes payload
    0x01 = INT    → 8 bytes (signed int64, big-endian)
    0x02 = FLOAT  → 8 bytes (double, big-endian)
    0x03 = TEXT   → 4 bytes length + UTF-8 bytes
    0x04 = BOOL   → 1 byte (0 or 1)

Row format:
    [2 bytes: total_data_length] [value1] [value2] ... [valueN]

Written at 2 AM with filter coffee. Tested at 4 AM with chai.
"""

import struct
from typing import Any, List, Tuple

from .constants import (
    TYPE_NULL,
    TYPE_INTEGER,
    TYPE_FLOAT,
    TYPE_TEXT,
    TYPE_BOOLEAN,
)
from .errors import DataUltaError


def encode_value(value: Any) -> bytes:
    """
    Encode a single Python value into its binary representation.

    Args:
        value: The value to encode. Can be None, int, float, str, or bool.

    Returns:
        bytes: The encoded value with type tag prefix.

    Raises:
        DataUltaError: If the value type is not supported.

    Example:
        >>> encode_value(42)
        b'\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00*'
        >>> encode_value(None)
        b'\\x00'
    """
    if value is None:
        return bytes([TYPE_NULL])

    # IMPORTANT: bool check MUST come before int check because
    # isinstance(True, int) is True in Python. Classic gotcha, macha.
    if isinstance(value, bool):
        return bytes([TYPE_BOOLEAN]) + struct.pack(">?", value)

    if isinstance(value, int):
        return bytes([TYPE_INTEGER]) + struct.pack(">q", value)

    if isinstance(value, float):
        return bytes([TYPE_FLOAT]) + struct.pack(">d", value)

    if isinstance(value, str):
        encoded = value.encode("utf-8")
        return bytes([TYPE_TEXT]) + struct.pack(">I", len(encoded)) + encoded

    raise DataUltaError(
        f"macha, '{type(value).__name__}' type encode maadak barthilla!"
    )


def decode_value(data: bytes, offset: int) -> Tuple[Any, int]:
    """
    Decode a single value from binary data at the given offset.

    Args:
        data: The binary data buffer.
        offset: Starting byte position.

    Returns:
        Tuple of (decoded_value, new_offset).

    Raises:
        DataUltaError: If the type tag is unrecognized (corruption!).
    """
    if offset >= len(data):
        raise DataUltaError("offset out of bounds — data truncated aagide!")

    type_tag = data[offset]
    offset += 1

    if type_tag == TYPE_NULL:
        return None, offset

    if type_tag == TYPE_INTEGER:
        value = struct.unpack(">q", data[offset : offset + 8])[0]
        return value, offset + 8

    if type_tag == TYPE_FLOAT:
        value = struct.unpack(">d", data[offset : offset + 8])[0]
        return value, offset + 8

    if type_tag == TYPE_TEXT:
        str_len = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        value = data[offset : offset + str_len].decode("utf-8")
        return value, offset + str_len

    if type_tag == TYPE_BOOLEAN:
        value = struct.unpack(">?", data[offset : offset + 1])[0]
        return value, offset + 1

    raise DataUltaError(
        f"unknown type tag 0x{type_tag:02x} — bewarsi, data corrupt aagide!"
    )


def encode_row(values: List[Any]) -> bytes:
    """
    Encode a complete row (list of values) into binary format.

    Format: [2 bytes: data_length] [encoded_value_1] [encoded_value_2] ...

    The 2-byte length prefix lets us quickly skip over rows during scanning
    without decoding every value. Smart, right? (We have our moments.)

    Args:
        values: List of Python values to encode.

    Returns:
        bytes: The complete encoded row with length prefix.
    """
    parts = []
    for val in values:
        parts.append(encode_value(val))

    data = b"".join(parts)
    # Length prefix: 2 bytes, big-endian unsigned short
    # Max row size: 65535 bytes. That's enough for anyone, boss.
    if len(data) > 65535:
        raise DataUltaError(
            f"row too big macha! {len(data)} bytes! Max 65535. "
            "Swalpa chikka maadu."
        )
    return struct.pack(">H", len(data)) + data


def decode_row(data: bytes, offset: int, num_columns: int) -> Tuple[List[Any], int]:
    """
    Decode a complete row from binary data.

    Args:
        data: The binary data buffer.
        offset: Starting byte position (at the length prefix).
        num_columns: Expected number of columns.

    Returns:
        Tuple of (list_of_values, new_offset_after_row).
    """
    # Read the row data length
    row_data_len = struct.unpack(">H", data[offset : offset + 2])[0]
    offset += 2
    end_offset = offset + row_data_len

    # Decode each value
    values = []
    for _ in range(num_columns):
        if offset >= end_offset:
            # Fewer values than columns — pad with None
            values.append(None)
            continue
        val, offset = decode_value(data, offset)
        values.append(val)

    # Advance to end of row data (skip any padding/extra bytes)
    return values, end_offset


def encoded_row_size(values: List[Any]) -> int:
    """
    Calculate the size of an encoded row WITHOUT actually encoding it.
    Useful for checking if a row fits in a page before committing.

    This is the fast path, macha. No memory allocation.
    """
    size = 2  # Length prefix
    for val in values:
        size += 1  # Type tag
        if val is None:
            pass  # NULL has no payload
        elif isinstance(val, bool):
            size += 1
        elif isinstance(val, int):
            size += 8
        elif isinstance(val, float):
            size += 8
        elif isinstance(val, str):
            size += 4 + len(val.encode("utf-8"))
        else:
            raise DataUltaError(f"can't size '{type(val).__name__}'")
    return size
