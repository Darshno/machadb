"""
godaamu.py — The Top-Level Database API of MachaDB

'Godaamu' means 'warehouse/godown'. This is the main entry point.
Users create a MachaDB instance, which opens the catalog and provides
an `execute()` method to run queries.

It also manages the active tables, buffer pools, and transactions.
"""

import os
from typing import Any, Dict

from .jamakhaana import Jamakhaana
from .notebook import Notebook
from .nenapu import Nenapu
from .shata import Shata
from .shortcut import Shortcut
from .artha_maadko import ArthaMaadko
from .kaamgarane import Kaamgarane
from .errors import MachaError


class MachaDB:
    """
    The main database class. The boss. The Godaamu.
    
    Usage:
        db = MachaDB("./data")
        result = db.execute("huttu jana (id sankhye, hesar pathya)")
    """

    def __init__(self, db_directory: str):
        self.db_directory = db_directory
        os.makedirs(db_directory, exist_ok=True)
        
        # Initialize catalog
        self.catalog = Jamakhaana(db_directory)
        
        # Cache of active table objects so we don't reopen files
        self._active_tables: Dict[str, Shata] = {}
        self._active_indexes: Dict[str, Dict[str, Shortcut]] = {}
        
        # The executor
        self.executor = Kaamgarane(self)

    def execute(self, query: str) -> Any:
        """
        The main API method. Parses and executes a Bangalore slang query.
        """
        query = query.strip()
        if not query:
            return "Khali query macha."
            
        try:
            # 1. Parse
            parser = ArthaMaadko(query)
            ast = parser.parse()
            
            # 2. Execute
            result = self.executor.execute(ast)
            return result
            
        except MachaError as e:
            # We catch our own errors and return them cleanly or re-raise
            # Let's re-raise so the REPL can print them nicely
            raise e
        except Exception as e:
            # Unexpected Python errors — full panic mode
            raise MachaError(f"ayyo macha, Python alli error aagide! {str(e)}")

    def _get_table(self, table_name: str) -> Shata:
        """
        Get an active Table instance, opening it if necessary.
        """
        table_name = table_name.lower()
        
        if table_name in self._active_tables:
            return self._active_tables[table_name]
            
        # Get schema and file path from catalog
        schema = self.catalog.get_schema(table_name)
        data_file = self.catalog.get_data_file(table_name)
        
        # Initialize Notebook and Nenapu
        notebook = Notebook(data_file)
        buffer_pool = Nenapu(notebook)
        
        # Initialize Table
        table = Shata(schema, notebook, buffer_pool)
        self._active_tables[table_name] = table
        
        return table

    def _close_table(self, table_name: str):
        """Close a table if it's open."""
        table_name = table_name.lower()
        if table_name in self._active_tables:
            self._active_tables[table_name].close()
            del self._active_tables[table_name]

    def _get_index(self, table_name: str, column_name: str) -> Shortcut:
        """Get an active index."""
        table_name = table_name.lower()
        if table_name not in self._active_indexes:
            self._active_indexes[table_name] = {}
            
        if column_name in self._active_indexes[table_name]:
            return self._active_indexes[table_name][column_name]
            
        idx_file = self.catalog.get_index_file(table_name, column_name)
        if not idx_file:
            raise MachaError(f"Index illa macha: {table_name}.{column_name}")
            
        shortcut = Shortcut(idx_file)
        self._active_indexes[table_name][column_name] = shortcut
        return shortcut

    def pakka(self):
        """
        COMMIT: Flush all dirty pages to disk across all active tables.
        """
        for table in self._active_tables.values():
            table.flush()
        for tbl_idxs in self._active_indexes.values():
            for idx in tbl_idxs.values():
                idx.flush()
            
    def beda(self):
        """
        ROLLBACK: Drop all dirty pages in buffer pools.
        This is a poor-man's rollback until Phase 6 WAL is ready.
        """
        for table in self._active_tables.values():
            table.pool.invalidate_all()

    def close(self):
        """Close the database safely."""
        for table in self._active_tables.values():
            table.close()
        self._active_tables.clear()
        
        for tbl_idxs in self._active_indexes.values():
            for idx in tbl_idxs.values():
                idx.close()
        self._active_indexes.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
