"""
shata.py — The Table Engine of MachaDB

'Shata' means 'table' in our universe. This is the heap file manager
that actually stores and retrieves rows of data.

A "heap file" is the simplest table organization: rows are stored
in pages in no particular order. New rows go into the last page
that has space. If no page has space, we allocate a new one.

This is exactly how PostgreSQL's heap tables work, macha.

Operations:
    insert(row_dict)     → Add a new row
    select(where_fn)     → Find rows matching a condition
    update(set_fn, where_fn) → Modify matching rows
    delete(where_fn)     → Remove matching rows (tombstone)
    full_scan()          → Read every row (the brute force way)
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from .constants import PAGE_HEADER_SIZE, ROW_HEADER_SIZE
from .types import Schema, DataType
from .page import Page
from .notebook import Notebook
from .nenapu import Nenapu
from .serializer import encode_row, encoded_row_size
from .errors import (
    ShataIllaError,
    ColumnIllaError,
    TypeMismatchError,
    PageFullError,
    DataUltaError,
)


class Shata:
    """
    The Table — a heap file that stores rows across multiple pages.

    Each table has:
      - A Schema (column definitions)
      - A Notebook (pager) for its .tbl file
      - A Nenapu (buffer pool) for caching hot pages
      - A lot of chai-fueled determination

    The table doesn't know about SQL or queries — it only knows
    about rows, columns, and pages. The parser and executor handle
    the fancy stuff.
    """

    def __init__(self, schema: Schema, notebook: Notebook, buffer_pool: Nenapu):
        """
        Initialize a table engine for a given schema and data file.

        Args:
            schema: The table's column definitions.
            notebook: The pager for disk I/O.
            buffer_pool: The LRU cache for page management.
        """
        self.schema = schema
        self.notebook = notebook
        self.pool = buffer_pool

    @property
    def name(self) -> str:
        return self.schema.table_name

    @property
    def column_count(self) -> int:
        return self.schema.column_count

    def insert(self, values: List[Any]) -> Tuple[int, int]:
        """
        Insert a row into the table.

        Finds the last page with space, or allocates a new page.
        Returns the (page_number, slot_index) where the row was stored.

        Args:
            values: List of values in column order.

        Returns:
            Tuple of (page_number, slot_index).

        Raises:
            TypeMismatchError: If a value doesn't match the column type.
        """
        # Validate values against schema
        self._validate_row(values)

        # Encode the row to binary
        encoded = encode_row(values)

        # Find a page with space — scan from the last page backward
        page = self._find_page_with_space(len(encoded))

        # Add the row to the page
        slot_index = page.add_row(encoded)

        # Mark the page as dirty in the buffer pool
        self.pool.put_page(page)

        return (page.page_id, slot_index)

    def insert_dict(self, row_dict: Dict[str, Any]) -> Tuple[int, int]:
        """
        Insert a row using a dictionary of column_name → value.

        This is the user-friendly version. Converts the dict to an
        ordered list of values based on the schema.

        Args:
            row_dict: Column name to value mapping.

        Returns:
            Tuple of (page_number, slot_index).
        """
        values = self._dict_to_row(row_dict)
        return self.insert(values)

    def select(
        self,
        columns: Optional[List[str]] = None,
        where_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Select rows from the table, optionally filtering and projecting.

        Args:
            columns: List of column names to return. None = all columns (*).
            where_fn: A function that takes a row dict and returns True to include.

        Returns:
            List of row dictionaries matching the criteria.
        """
        results = []

        for _page_id, _slot, row_dict in self._full_scan():
            # Apply WHERE filter
            if where_fn and not where_fn(row_dict):
                continue

            # Apply column projection
            if columns:
                projected = {}
                for col in columns:
                    if col in row_dict:
                        projected[col] = row_dict[col]
                    else:
                        raise ColumnIllaError(col, self.name)
                results.append(projected)
            else:
                results.append(row_dict)

        return results

    def update(
        self,
        set_values: Dict[str, Any],
        where_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """
        Update rows matching the WHERE condition.

        Strategy: find matching rows, delete the old version,
        insert the new version. This is the "delete + re-insert"
        approach used by many databases for simplicity.

        Args:
            set_values: Dict of column_name → new_value.
            where_fn: Filter function. None = update ALL rows (dangerous, boss!).

        Returns:
            Number of rows updated.
        """
        # Validate the SET columns exist and types match
        for col_name, val in set_values.items():
            col = self.schema.get_column(col_name)
            if col is None:
                raise ColumnIllaError(col_name, self.name)
            if val is not None and not col.validate(val):
                raise TypeMismatchError(
                    col_name,
                    col.data_type.value,
                    type(val).__name__,
                )

        updated_count = 0
        rows_to_update = []

        # First pass: find rows to update (collect page_id, slot, old_values)
        for page_id, slot_idx, row_dict in self._full_scan():
            if where_fn is None or where_fn(row_dict):
                rows_to_update.append((page_id, slot_idx, row_dict))

        # Second pass: delete old, insert new
        for page_id, slot_idx, old_dict in rows_to_update:
            # Build new row
            new_dict = dict(old_dict)
            new_dict.update(set_values)

            # Delete old row (tombstone)
            page = self.pool.get_page(page_id)
            page.delete_row(slot_idx)
            self.pool.put_page(page)

            # Insert updated row
            new_values = [new_dict[col.name] for col in self.schema.columns]
            self.insert(new_values)
            updated_count += 1

        return updated_count

    def delete(
        self,
        where_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """
        Delete rows matching the WHERE condition.

        Uses tombstone approach — marks rows as deleted without
        physically removing them. Space is reclaimed on compaction.

        Args:
            where_fn: Filter function. None = delete ALL rows (full destruction!).

        Returns:
            Number of rows deleted.
        """
        deleted_count = 0

        for page_id, slot_idx, row_dict in self._full_scan():
            if where_fn is None or where_fn(row_dict):
                page = self.pool.get_page(page_id)
                if page.delete_row(slot_idx):
                    self.pool.put_page(page)
                    deleted_count += 1

        return deleted_count

    def full_scan_rows(self) -> List[Tuple[int, int, List[Any]]]:
        """
        Scan all active rows and return raw values with location info.

        Returns:
            List of (page_id, slot_index, values_list) tuples.
        """
        results = []
        for page_id in range(1, self.notebook.total_pages):
            page = self.pool.get_page(page_id)
            for slot_idx, values in page.get_all_rows(self.column_count):
                results.append((page_id, slot_idx, values))
        return results

    def get_row_by_ptr(self, page_id: int, slot_idx: int) -> Optional[Dict[str, Any]]:
        """
        Fast O(1) point lookup using a B-Tree pointer.
        """
        page = self.pool.get_page(page_id)
        values = page.get_row_by_slot(slot_idx, self.column_count)
        if values is None:
            return None
        return dict(zip(self.schema.column_names, values))

    # ================================================================
    # Internal Methods — the chai-powered engine room
    # ================================================================

    def _full_scan(self):
        """
        Generator that yields (page_id, slot_index, row_dict) for all active rows.

        This is the core scan operation. Every SELECT without an index
        goes through this. It's O(n) where n = total rows, which is
        why indexes exist, macha.
        """
        col_names = self.schema.column_names

        for page_id in range(1, self.notebook.total_pages):
            page = self.pool.get_page(page_id)
            for slot_idx, values in page.get_all_rows(self.column_count):
                # Convert values list to dict
                row_dict = dict(zip(col_names, values))
                yield page_id, slot_idx, row_dict

    def _find_page_with_space(self, row_size: int) -> Page:
        """
        Find a page that has room for a new row, or allocate one.

        Strategy: check the last page first (most likely to have space).
        If it's full, allocate a new page.

        Args:
            row_size: Total size of the encoded row in bytes.

        Returns:
            A Page with enough space.
        """
        total_needed = 1 + row_size  # status byte + encoded row

        # If there are data pages, check the last one
        if self.notebook.total_pages > 1:
            last_page_id = self.notebook.total_pages - 1
            last_page = self.pool.get_page(last_page_id)
            if last_page.has_space_for(row_size):
                return last_page

        # No space in existing pages — allocate a new one
        new_page = self.pool.new_page()
        return new_page

    def _validate_row(self, values: List[Any]):
        """Validate a row of values against the schema."""
        if len(values) != self.column_count:
            raise DataUltaError(
                f"expected {self.column_count} values, got {len(values)}. "
                f"Columns: {self.schema.column_names}"
            )

        for col, val in zip(self.schema.columns, values):
            if val is not None and not col.validate(val):
                raise TypeMismatchError(
                    col.name,
                    col.data_type.value,
                    type(val).__name__,
                )

    def _dict_to_row(self, row_dict: Dict[str, Any]) -> List[Any]:
        """Convert a {column_name: value} dict to an ordered values list."""
        values = []
        for col in self.schema.columns:
            if col.name in row_dict:
                values.append(row_dict[col.name])
            elif col.is_nullable:
                values.append(None)
            else:
                raise DataUltaError(
                    f"column '{col.name}' is required macha, but you didn't give it!"
                )
        return values

    def count(self) -> int:
        """Count all active rows. Full scan, but sometimes you gotta count."""
        count = 0
        for page_id in range(1, self.notebook.total_pages):
            page = self.pool.get_page(page_id)
            count += len(page.get_all_rows(self.column_count))
        return count

    def flush(self):
        """Flush all dirty pages for this table to disk."""
        self.pool.flush_all()

    def close(self):
        """Close the table — flush and release resources."""
        self.pool.close()
        self.notebook.close()

    def __repr__(self) -> str:
        return (
            f"Shata('{self.name}', columns={self.schema.column_names}, "
            f"pages={self.notebook.data_page_count})"
        )
