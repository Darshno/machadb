"""
page.py — The 4KB Page: Fundamental Unit of MachaDB

Every real database operates in pages — fixed-size blocks of bytes.
Not rows, not records, PAGES. This is how SQLite, PostgreSQL, MySQL
all work under the hood.

Why 4096 bytes?
  - Matches OS memory page size (Linux, Windows)
  - Matches SSD sector size
  - Our seniors picked it and we're too scared to ask why

Page Layout:
    ┌──────────────────────────────────┐  byte 0
    │  row_count (2 bytes)             │
    │  free_offset (2 bytes)           │
    │  page_id (4 bytes)               │
    ├──────────────────────────────────┤  byte 8 (PAGE_HEADER_SIZE)
    │  Row 0:                          │
    │    [status: 1 byte]              │
    │    [data_len: 2 bytes]           │
    │    [data: N bytes]               │
    ├──────────────────────────────────┤
    │  Row 1:                          │
    │    [status: 1 byte]              │
    │    [data_len: 2 bytes]           │
    │    [data: N bytes]               │
    ├──────────────────────────────────┤
    │  ... more rows ...               │
    ├──────────────────────────────────┤
    │  Free space                      │
    │  (filled with zeros)             │
    └──────────────────────────────────┘  byte 4095

Status byte:
    0x00 = ACTIVE (row is alive and well, like us after chai)
    0x01 = DELETED (row is dead, like our sleep schedule)
"""

import struct
from typing import Any, List, Optional, Tuple

from .constants import (
    PAGE_SIZE,
    PAGE_HEADER_SIZE,
    ROW_HEADER_SIZE,
    ROW_STATUS_ACTIVE,
    ROW_STATUS_DELETED,
)
from .serializer import encode_row, decode_row, encoded_row_size
from .errors import PageFullError, DataUltaError


class Page:
    """
    A 4096-byte page that holds rows of data.

    This is the atomic unit of I/O in MachaDB. When we read from disk,
    we read a whole page. When we write to disk, we write a whole page.
    No partial reads. No partial writes. Full commitment, macha.
    """

    def __init__(self, page_id: int = 0):
        """Create a fresh, empty page."""
        self.page_id = page_id
        self.data = bytearray(PAGE_SIZE)
        self.row_count = 0
        self.free_offset = PAGE_HEADER_SIZE
        self.dirty = False
        self._write_header()

    def _write_header(self):
        """Write the page header into the byte buffer."""
        struct.pack_into(
            ">HHI", self.data, 0,
            self.row_count, self.free_offset, self.page_id,
        )

    def _read_header(self):
        """Read the page header from the byte buffer."""
        self.row_count, self.free_offset, self.page_id = struct.unpack_from(
            ">HHI", self.data, 0,
        )

    @classmethod
    def from_bytes(cls, data: bytes, page_id: int = 0) -> "Page":
        """
        Deserialize a page from raw bytes (read from disk).

        Args:
            data: Exactly PAGE_SIZE bytes.
            page_id: The page number (used for tracking).

        Returns:
            A fully initialized Page.
        """
        if len(data) != PAGE_SIZE:
            raise DataUltaError(
                f"page size mismatch! expected {PAGE_SIZE}, got {len(data)}. "
                "File corrupt aagide macha!"
            )
        page = cls.__new__(cls)
        page.data = bytearray(data)
        page.page_id = page_id
        page.dirty = False
        page._read_header()
        return page

    def has_space_for(self, row_data_size: int) -> bool:
        """
        Check if this page can fit a new row.

        Args:
            row_data_size: Size of the encoded row data (from encode_row).

        Returns:
            True if there's enough room.
        """
        # Row needs: status(1) + the encoded row bytes (which include the 2-byte length prefix)
        total_needed = 1 + row_data_size  # status byte + encoded row (already includes len prefix)
        return (self.free_offset + total_needed) <= PAGE_SIZE

    def add_row(self, encoded_row: bytes) -> int:
        """
        Add an encoded row to this page.

        Args:
            encoded_row: Output of serializer.encode_row() — includes length prefix.

        Returns:
            The slot index (0-based position) of the newly added row.

        Raises:
            PageFullError: If there's no space left.
        """
        total_needed = 1 + len(encoded_row)  # status byte + encoded row
        if self.free_offset + total_needed > PAGE_SIZE:
            raise PageFullError(self.page_id)

        slot_index = self.row_count
        offset = self.free_offset

        # Write status byte
        self.data[offset] = ROW_STATUS_ACTIVE
        offset += 1

        # Write the encoded row (which already has the 2-byte length prefix)
        self.data[offset : offset + len(encoded_row)] = encoded_row
        offset += len(encoded_row)

        # Update header
        self.row_count += 1
        self.free_offset = offset
        self.dirty = True
        self._write_header()

        return slot_index

    def get_all_rows(self, num_columns: int) -> List[Tuple[int, List[Any]]]:
        """
        Read all ACTIVE rows from this page.

        Args:
            num_columns: Number of columns per row (needed for deserialization).

        Returns:
            List of (slot_index, row_values) tuples.
            Only includes active (non-deleted) rows.
        """
        rows = []
        offset = PAGE_HEADER_SIZE

        for slot_idx in range(self.row_count):
            status = self.data[offset]
            offset += 1  # Skip status byte

            # Read row data length from the encoded row's length prefix
            row_data_len = struct.unpack(">H", self.data[offset : offset + 2])[0]
            row_total_len = 2 + row_data_len  # length prefix + data

            if status == ROW_STATUS_ACTIVE:
                values, _ = decode_row(self.data, offset, num_columns)
                rows.append((slot_idx, values))

            offset += row_total_len

        return rows

    def get_row_by_slot(self, slot_index: int, num_columns: int) -> Optional[List[Any]]:
        """
        Get a specific row by its slot index.

        Args:
            slot_index: The 0-based slot position.
            num_columns: Number of columns per row.

        Returns:
            The row values if active, None if deleted or out of range.
        """
        if slot_index >= self.row_count:
            return None

        offset = PAGE_HEADER_SIZE
        for i in range(slot_index):
            offset += 1  # status byte
            row_data_len = struct.unpack(">H", self.data[offset : offset + 2])[0]
            offset += 2 + row_data_len

        status = self.data[offset]
        offset += 1

        if status == ROW_STATUS_DELETED:
            return None

        values, _ = decode_row(self.data, offset, num_columns)
        return values

    def delete_row(self, slot_index: int) -> bool:
        """
        Mark a row as deleted (tombstone approach).

        We don't actually remove the bytes — that would shift everything.
        Instead, we just flip the status byte. Lazy? Maybe.
        Efficient? Absolutely, macha.

        Args:
            slot_index: The 0-based slot index of the row to delete.

        Returns:
            True if the row was deleted, False if already deleted or not found.
        """
        if slot_index >= self.row_count:
            return False

        offset = PAGE_HEADER_SIZE
        for i in range(slot_index):
            offset += 1  # status byte
            row_data_len = struct.unpack(">H", self.data[offset : offset + 2])[0]
            offset += 2 + row_data_len

        if self.data[offset] == ROW_STATUS_DELETED:
            return False  # Already dead, macha

        self.data[offset] = ROW_STATUS_DELETED
        self.dirty = True
        return True

    def get_raw_row_at_slot(self, slot_index: int) -> Optional[bytes]:
        """
        Get the raw encoded bytes of a row (for WAL before/after images).

        Returns:
            Raw bytes including status + encoded_row, or None.
        """
        if slot_index >= self.row_count:
            return None

        offset = PAGE_HEADER_SIZE
        for i in range(slot_index):
            offset += 1
            row_data_len = struct.unpack(">H", self.data[offset : offset + 2])[0]
            offset += 2 + row_data_len

        start = offset
        status = self.data[offset]
        offset += 1
        row_data_len = struct.unpack(">H", self.data[offset : offset + 2])[0]
        offset += 2 + row_data_len
        return bytes(self.data[start:offset])

    def to_bytes(self) -> bytes:
        """Serialize this page to bytes for writing to disk."""
        self._write_header()
        return bytes(self.data)

    @property
    def free_space(self) -> int:
        """How many bytes are free in this page."""
        return PAGE_SIZE - self.free_offset

    def __repr__(self) -> str:
        return (
            f"Page(id={self.page_id}, rows={self.row_count}, "
            f"free={self.free_space}, dirty={self.dirty})"
        )
