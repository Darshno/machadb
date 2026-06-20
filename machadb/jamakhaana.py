"""
jamakhaana.py — The Catalog (System Metadata Store) of MachaDB

'Jamakhaana' means 'inventory/warehouse' — this is where we keep
track of what tables exist, their schemas, and their file paths.

Think of it as the receptionist at a Darshini restaurant who knows
exactly which table is free, what's on the menu, and where the
filter coffee machine is.

The catalog is persisted as a JSON file (jamakhaana.json) so it
survives process restarts. Every CREATE TABLE and DROP TABLE
updates this file.
"""

import json
import os
from typing import Dict, List, Optional

from .constants import CATALOG_FILENAME
from .types import Schema, Column, DataType
from .errors import ShataIllaError, DuplicateError


class Jamakhaana:
    """
    The System Catalog — knows everything about every table.

    Responsibilities:
      - Track all table schemas
      - Map table names to data file paths
      - Persist metadata to jamakhaana.json
      - Survive restarts like a cockroach survives everything

    All catalog operations are immediately persisted to disk.
    We don't trust RAM alone — that's how you lose data at 3 AM, macha.
    """

    def __init__(self, db_directory: str):
        """
        Open (or create) the catalog for a database directory.

        Args:
            db_directory: Path to the database directory.
        """
        self.db_directory = db_directory
        self._catalog_path = os.path.join(db_directory, CATALOG_FILENAME)
        self._tables: Dict[str, dict] = {}  # table_name → metadata
        self._indexes: Dict[str, list] = {}  # table_name → list of index info

        # Create directory if needed
        os.makedirs(db_directory, exist_ok=True)

        # Load existing catalog or initialize empty
        if os.path.exists(self._catalog_path):
            self._load()
        else:
            self._save()

    def _load(self):
        """Load catalog from disk."""
        try:
            with open(self._catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._tables = data.get("tables", {})
            self._indexes = data.get("indexes", {})
        except (json.JSONDecodeError, IOError) as e:
            raise ShataIllaError(
                f"catalog corrupt aagide macha! {e}"
            )

    def _save(self):
        """Persist catalog to disk. Immediate write, no lazy stuff."""
        data = {
            "magic": "MACHADB_JAMAKHAANA",
            "version": 1,
            "tables": self._tables,
            "indexes": self._indexes,
        }
        # Write to temp file first, then rename (atomic on most OS)
        tmp_path = self._catalog_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomic rename
        if os.path.exists(self._catalog_path):
            os.replace(tmp_path, self._catalog_path)
        else:
            os.rename(tmp_path, self._catalog_path)

    def create_table(self, schema: Schema) -> str:
        """
        Register a new table in the catalog.

        Args:
            schema: The Schema object defining the table structure.

        Returns:
            The file path for the table's data file.

        Raises:
            DuplicateError: If a table with the same name already exists.
        """
        table_name = schema.table_name.lower()

        if table_name in self._tables:
            raise DuplicateError(table_name, "shata (table)")

        # Data file path
        data_file = os.path.join(self.db_directory, f"{table_name}.tbl")

        self._tables[table_name] = {
            "schema": schema.to_dict(),
            "data_file": data_file,
            "row_count": 0,
        }

        self._save()
        return data_file

    def drop_table(self, table_name: str):
        """
        Remove a table from the catalog and delete its data file.

        Args:
            table_name: Name of the table to drop.

        Raises:
            ShataIllaError: If the table doesn't exist.
        """
        table_name = table_name.lower()

        if table_name not in self._tables:
            raise ShataIllaError(table_name)

        # Get file path before removing from catalog
        data_file = self._tables[table_name]["data_file"]

        # Remove from catalog
        del self._tables[table_name]

        # Remove any indexes for this table
        if table_name in self._indexes:
            for idx_info in self._indexes[table_name]:
                idx_file = idx_info.get("file")
                if idx_file and os.path.exists(idx_file):
                    os.remove(idx_file)
            del self._indexes[table_name]

        self._save()

        # Delete the data file
        if os.path.exists(data_file):
            os.remove(data_file)

    def get_schema(self, table_name: str) -> Schema:
        """
        Get the schema for a table.

        Args:
            table_name: Name of the table.

        Returns:
            The Schema object.

        Raises:
            ShataIllaError: If the table doesn't exist.
        """
        table_name = table_name.lower()

        if table_name not in self._tables:
            raise ShataIllaError(table_name)

        return Schema.from_dict(self._tables[table_name]["schema"])

    def get_data_file(self, table_name: str) -> str:
        """Get the data file path for a table."""
        table_name = table_name.lower()

        if table_name not in self._tables:
            raise ShataIllaError(table_name)

        return self._tables[table_name]["data_file"]

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        return table_name.lower() in self._tables

    def list_tables(self) -> List[str]:
        """List all table names. For the 'yenide' (show tables) command."""
        return sorted(self._tables.keys())

    def update_row_count(self, table_name: str, delta: int):
        """
        Update the row count for a table.

        Args:
            table_name: Table name.
            delta: Change in row count (+1 for insert, -1 for delete).
        """
        table_name = table_name.lower()
        if table_name in self._tables:
            self._tables[table_name]["row_count"] = max(
                0, self._tables[table_name].get("row_count", 0) + delta
            )
            self._save()

    def get_row_count(self, table_name: str) -> int:
        """Get the stored row count for a table."""
        table_name = table_name.lower()
        if table_name not in self._tables:
            raise ShataIllaError(table_name)
        return self._tables[table_name].get("row_count", 0)

    # ================================================================
    # Index Management
    # ================================================================

    def register_index(self, table_name: str, column_name: str, index_file: str):
        """Register a new index in the catalog."""
        table_name = table_name.lower()
        if table_name not in self._indexes:
            self._indexes[table_name] = []

        # Check for duplicate
        for idx in self._indexes[table_name]:
            if idx["column"] == column_name:
                raise DuplicateError(f"{table_name}.{column_name}", "index")

        self._indexes[table_name].append({
            "column": column_name,
            "file": index_file,
        })
        self._save()

    def get_index_file(self, table_name: str, column_name: str) -> Optional[str]:
        """Get the index file path for a column, or None if not indexed."""
        table_name = table_name.lower()
        for idx in self._indexes.get(table_name, []):
            if idx["column"] == column_name:
                return idx["file"]
        return None

    def has_index(self, table_name: str, column_name: str) -> bool:
        """Check if a column has an index."""
        return self.get_index_file(table_name, column_name) is not None

    def list_indexes(self, table_name: str) -> List[dict]:
        """List all indexes for a table."""
        table_name = table_name.lower()
        return self._indexes.get(table_name, [])

    def get_table_info(self, table_name: str) -> dict:
        """Get full metadata about a table (for debugging/status)."""
        table_name = table_name.lower()
        if table_name not in self._tables:
            raise ShataIllaError(table_name)

        info = dict(self._tables[table_name])
        info["indexes"] = self._indexes.get(table_name, [])
        return info

    def __repr__(self) -> str:
        return f"Jamakhaana(tables={self.list_tables()})"
