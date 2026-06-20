"""
notebook.py — The Pager (Disk I/O Engine) of MachaDB

Named 'notebook' because this is where we write things down
so we don't forget them when the process dies. Like a notebook
you carry to class but actually use.

The Pager is responsible for:
  1. Mapping page numbers to byte offsets in a file
  2. Reading pages from disk
  3. Writing pages to disk
  4. Managing the file header (page 0)

File Layout:
    ┌─────────────────────┐  offset 0
    │  File Header (Page 0)│
    │  - Magic: 'MCHA'    │
    │  - Version: 1        │
    │  - Page count        │
    │  - Schema info       │
    ├─────────────────────┤  offset 4096
    │  Data Page 1         │
    ├─────────────────────┤  offset 8192
    │  Data Page 2         │
    ├─────────────────────┤
    │  ...                 │
    └─────────────────────┘

Page N lives at byte offset: N * PAGE_SIZE
Simple. Clean. Like filter coffee.
"""

import os
import struct
from typing import Optional

from .constants import PAGE_SIZE, MAGIC_BYTES, FILE_VERSION, FILE_HEADER_FIXED_SIZE
from .page import Page
from .errors import FileCorruptError, DataUltaError


class Notebook:
    """
    The Pager — reads and writes pages to a file on disk.

    Every .tbl file is managed by one Notebook instance.
    It handles all the low-level file I/O so the rest of
    the system doesn't have to think about bytes and offsets.

    Like that one friend in the group project who actually
    does the work.
    """

    def __init__(self, filepath: str):
        """
        Open (or create) a database file.

        Args:
            filepath: Path to the .tbl file.
        """
        self.filepath = filepath
        self.total_pages = 0
        self._file = None
        self._is_new = not os.path.exists(filepath)

        # Create directory if it doesn't exist
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        # Open the file (create if needed)
        if self._is_new:
            self._file = open(filepath, "w+b")
            self._init_file_header()
        else:
            self._file = open(filepath, "r+b")
            self._read_file_header()

    def _init_file_header(self):
        """
        Write the initial file header to page 0.

        Header layout (within page 0):
            [4 bytes: MAGIC 'MCHA']
            [1 byte:  VERSION]
            [4 bytes: total_pages (initially 1, just the header)]
            [4 bytes: total_rows]
            [2 bytes: reserved]
        """
        header = bytearray(PAGE_SIZE)
        offset = 0

        # Magic bytes
        header[offset : offset + 4] = MAGIC_BYTES
        offset += 4

        # Version
        header[offset] = FILE_VERSION
        offset += 1

        # Total pages (1 = just the header page)
        struct.pack_into(">I", header, offset, 1)
        offset += 4

        # Total rows
        struct.pack_into(">I", header, offset, 0)
        offset += 4

        # Reserved
        struct.pack_into(">H", header, offset, 0)

        self._file.seek(0)
        self._file.write(header)
        self._file.flush()
        self.total_pages = 1

    def _read_file_header(self):
        """
        Read and validate the file header from page 0.

        Raises:
            FileCorruptError: If magic bytes don't match or version is wrong.
        """
        self._file.seek(0)
        header = self._file.read(PAGE_SIZE)

        if len(header) < FILE_HEADER_FIXED_SIZE:
            raise FileCorruptError(
                self.filepath, "header too short — file truncated aagide!"
            )

        # Check magic bytes
        magic = header[0:4]
        if magic != MAGIC_BYTES:
            raise FileCorruptError(
                self.filepath,
                f"expected magic '{MAGIC_BYTES.decode()}', got '{magic}'. "
                "Idhu MachaDB file alla boss!"
            )

        # Check version
        version = header[4]
        if version != FILE_VERSION:
            raise FileCorruptError(
                self.filepath,
                f"version mismatch! file has v{version}, we need v{FILE_VERSION}. "
                "Update madu macha."
            )

        # Read page count
        self.total_pages = struct.unpack(">I", header[5:9])[0]

    def _update_file_header(self):
        """Update the page count in the file header."""
        self._file.seek(5)  # Skip magic(4) + version(1)
        self._file.write(struct.pack(">I", self.total_pages))
        self._file.flush()

    def read_page(self, page_number: int) -> Page:
        """
        Read a page from disk by its page number.

        Args:
            page_number: 0-based page index. Page 0 is the file header.

        Returns:
            A Page object loaded with data from disk.

        Raises:
            DataUltaError: If page_number is out of range.
        """
        if page_number < 0 or page_number >= self.total_pages:
            raise DataUltaError(
                f"page {page_number} illa macha! Total pages: {self.total_pages}"
            )

        offset = page_number * PAGE_SIZE
        self._file.seek(offset)
        data = self._file.read(PAGE_SIZE)

        if len(data) < PAGE_SIZE:
            # Pad with zeros if file is truncated (shouldn't happen, but bewarsi)
            data = data + b"\x00" * (PAGE_SIZE - len(data))

        return Page.from_bytes(data, page_number)

    def write_page(self, page: Page):
        """
        Write a page to disk at its designated position.

        Args:
            page: The Page object to write. Uses page.page_id for positioning.
        """
        offset = page.page_id * PAGE_SIZE
        self._file.seek(offset)
        self._file.write(page.to_bytes())
        self._file.flush()
        page.dirty = False

    def allocate_page(self) -> Page:
        """
        Allocate a new empty page at the end of the file.

        Returns:
            A fresh, empty Page with its page_id set.
        """
        page_id = self.total_pages
        page = Page(page_id=page_id)

        # Write the empty page to disk immediately to extend the file
        offset = page_id * PAGE_SIZE
        self._file.seek(offset)
        self._file.write(page.to_bytes())

        self.total_pages += 1
        self._update_file_header()

        return page

    def sync(self):
        """Flush all buffered writes to disk. Full sync, macha."""
        if self._file:
            self._file.flush()
            os.fsync(self._file.fileno())

    def close(self):
        """Close the file. Goodbye macha, see you next time."""
        if self._file:
            self.sync()
            self._file.close()
            self._file = None

    @property
    def data_page_count(self) -> int:
        """Number of data pages (excluding the header page)."""
        return max(0, self.total_pages - 1)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __repr__(self) -> str:
        return (
            f"Notebook('{self.filepath}', pages={self.total_pages}, "
            f"data_pages={self.data_page_count})"
        )

    def __del__(self):
        self.close()
