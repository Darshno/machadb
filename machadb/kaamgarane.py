"""
kaamgarane.py — The Execution Engine of MachaDB

'Kaamgarane' means 'the worker'. This module takes the parsed AST
and actually executes it against the Table and Catalog APIs.

This is the bridge between "I want to do this" (AST) and
"Here's the data" (Storage layer).
"""

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from .ast_nodes import (
    Statement, HuttuStatement, HuttuShortcutStatement, HaakuStatement, TorsuStatement,
    ChangeMaaduStatement, EnKilthyaStatement, SutakuStatement,
    SystemStatement, TransactionStatement, Expression,
    Literal, ColumnRef, BinaryExpr
)
from .types import Schema, Column
from .jamakhaana import Jamakhaana
from .shata import Shata
from .errors import (
    MachaError,
    SyntaxBejaarError,
    ColumnIllaError,
    TypeMismatchError
)

class Kaamgarane:
    """
    The Executor.
    Takes an AST node and executes it on the database.
    """
    def __init__(self, godaamu):
        """
        Takes a reference to Godaamu (the Database instance)
        so it can access catalog, buffer pool, etc.
        """
        self.db = godaamu

    def execute(self, stmt: Statement) -> Any:
        """Dispatch execution based on AST node type."""
        
        if isinstance(stmt, HuttuStatement):
            return self._exec_huttu(stmt)
            
        elif isinstance(stmt, HuttuShortcutStatement):
            return self._exec_huttu_shortcut(stmt)
            
        elif isinstance(stmt, HaakuStatement):
            return self._exec_haaku(stmt)
            
        elif isinstance(stmt, TorsuStatement):
            return self._exec_torsu(stmt)
            
        elif isinstance(stmt, ChangeMaaduStatement):
            return self._exec_change_madu(stmt)
            
        elif isinstance(stmt, EnKilthyaStatement):
            return self._exec_en_kilthya(stmt)
            
        elif isinstance(stmt, SutakuStatement):
            return self._exec_sutaku(stmt)
            
        elif isinstance(stmt, SystemStatement):
            return self._exec_system(stmt)
            
        elif isinstance(stmt, TransactionStatement):
            return self._exec_transaction(stmt)
            
        else:
            raise MachaError(f"Macha, '{type(stmt).__name__}' execute maadak barthilla!")

    # --- Statement Executors ---

    def _exec_huttu(self, stmt: HuttuStatement) -> str:
        # Create Schema
        schema = Schema(stmt.table_name, [
            Column(name=c.name, data_type=c.data_type) for c in stmt.columns
        ])
        
        # Register in catalog
        self.db.catalog.create_table(schema)
        return "✔ hosa shata ready macha"

    def _exec_haaku(self, stmt: HaakuStatement) -> str:
        table = self.db._get_table(stmt.table_name)
        
        # Evaluate values
        values = [self._eval_expr(expr, {}) for expr in stmt.values]
        
        # Insert into table
        page_id, slot_idx = table.insert(values)
        self.db.catalog.update_row_count(stmt.table_name, 1)
        
        # Insert into indexes
        row_dict = dict(zip(table.schema.column_names, values))
        for idx_info in self.db.catalog.list_indexes(stmt.table_name):
            col_name = idx_info["column"]
            shortcut = self.db._get_index(stmt.table_name, col_name)
            shortcut.insert(row_dict[col_name], (page_id, slot_idx))
        
        return "✔ haakidini macha"

    def _exec_huttu_shortcut(self, stmt: HuttuShortcutStatement) -> str:
        # Validate column
        schema = self.db.catalog.get_schema(stmt.table_name)
        if not schema.get_column(stmt.column_name):
            raise ColumnIllaError(stmt.column_name, stmt.table_name)
            
        # Register in catalog
        idx_file = os.path.join(self.db.db_directory, f"{stmt.table_name}_{stmt.column_name}.idx")
        self.db.catalog.register_index(stmt.table_name, stmt.column_name, idx_file)
        
        # Populate the index
        shortcut = self.db._get_index(stmt.table_name, stmt.column_name)
        table = self.db._get_table(stmt.table_name)
        
        count = 0
        for page_id, slot_idx, row_dict in table._full_scan():
            shortcut.insert(row_dict[stmt.column_name], (page_id, slot_idx))
            count += 1
            
        return f"✔ shortcut ready macha ({count} rows indexed)"

    def _exec_torsu(self, stmt: TorsuStatement) -> List[Dict[str, Any]]:
        table = self.db._get_table(stmt.table_name)
        
        columns = None if not stmt.columns else stmt.columns
        
        # Check if we can use an index (Shortcut)
        indexed_col = None
        indexed_val = None
        if stmt.where_expr and isinstance(stmt.where_expr, BinaryExpr) and stmt.where_expr.operator == "=":
            if isinstance(stmt.where_expr.left, ColumnRef) and isinstance(stmt.where_expr.right, Literal):
                indexed_col = stmt.where_expr.left.column_name
                indexed_val = stmt.where_expr.right.value
                
        if indexed_col and self.db.catalog.has_index(stmt.table_name, indexed_col):
            # O(log n) lookup
            shortcut = self.db._get_index(stmt.table_name, indexed_col)
            ptrs = shortcut.search(indexed_val)
            
            results = []
            for page_id, slot_idx in ptrs:
                row_dict = table.get_row_by_ptr(page_id, slot_idx)
                if row_dict:
                    if columns:
                        results.append({c: row_dict[c] for c in columns if c in row_dict})
                    else:
                        results.append(row_dict)
            return results

        # Fallback to O(n) full scan
        where_fn = None
        if stmt.where_expr:
            # Create a closure that evaluates the expression for each row
            def build_where_fn(expr):
                return lambda row_dict: self._eval_expr(expr, row_dict)
            where_fn = build_where_fn(stmt.where_expr)
            
        results = table.select(columns=columns, where_fn=where_fn)
        return results

    def _exec_change_madu(self, stmt: ChangeMaaduStatement) -> str:
        table = self.db._get_table(stmt.table_name)
        
        set_val = self._eval_expr(stmt.set_value, {})
        set_dict = {stmt.set_column: set_val}
        
        # To update indexes, we need to manually find rows and do delete+insert on the index
        # This is where database engines get complicated boss.
        
        # First, find rows to update
        where_fn = None
        if stmt.where_expr:
            def build_where_fn(expr):
                return lambda row_dict: self._eval_expr(expr, row_dict)
            where_fn = build_where_fn(stmt.where_expr)
            
        rows_to_update = []
        for page_id, slot_idx, row_dict in table._full_scan():
            if where_fn is None or where_fn(row_dict):
                rows_to_update.append((page_id, slot_idx, row_dict))
                
        # Get active indexes for this table
        indexes = []
        for idx_info in self.db.catalog.list_indexes(stmt.table_name):
            indexes.append((idx_info["column"], self.db._get_index(stmt.table_name, idx_info["column"])))
            
        updated_count = 0
        for page_id, slot_idx, old_dict in rows_to_update:
            # Delete old index entries
            for col_name, shortcut in indexes:
                shortcut.delete(old_dict[col_name], (page_id, slot_idx))
                
            # Perform table update (which deletes old and inserts new)
            # We bypass table.update() because it does its own scan. We do it manually:
            page = table.pool.get_page(page_id)
            page.delete_row(slot_idx)
            table.pool.put_page(page)
            
            new_dict = dict(old_dict)
            new_dict.update(set_dict)
            new_values = [new_dict[col.name] for col in table.schema.columns]
            new_page_id, new_slot_idx = table.insert(new_values)
            
            # Insert new index entries
            for col_name, shortcut in indexes:
                shortcut.insert(new_dict[col_name], (new_page_id, new_slot_idx))
                
            updated_count += 1
            
        return f"✔ change maadidini boss ({updated_count} rows)"

    def _exec_en_kilthya(self, stmt: EnKilthyaStatement) -> str:
        table = self.db._get_table(stmt.table_name)
        
        where_fn = None
        if stmt.where_expr:
            def build_where_fn(expr):
                return lambda row_dict: self._eval_expr(expr, row_dict)
            where_fn = build_where_fn(stmt.where_expr)
            
        # Get active indexes
        indexes = []
        for idx_info in self.db.catalog.list_indexes(stmt.table_name):
            indexes.append((idx_info["column"], self.db._get_index(stmt.table_name, idx_info["column"])))
            
        deleted_count = 0
        for page_id, slot_idx, row_dict in table._full_scan():
            if where_fn is None or where_fn(row_dict):
                # Delete from table
                page = table.pool.get_page(page_id)
                if page.delete_row(slot_idx):
                    table.pool.put_page(page)
                    deleted_count += 1
                    
                    # Delete from indexes
                    for col_name, shortcut in indexes:
                        shortcut.delete(row_dict[col_name], (page_id, slot_idx))
                        
        self.db.catalog.update_row_count(stmt.table_name, -deleted_count)
        return f"✔ kilkond hakidini macha ({deleted_count} rows)"

    def _exec_sutaku(self, stmt: SutakuStatement) -> str:
        self.db._close_table(stmt.table_name)
        self.db.catalog.drop_table(stmt.table_name)
        return f"✔ '{stmt.table_name}' table swaha!"

    def _exec_system(self, stmt: SystemStatement) -> Any:
        cmd = stmt.command
        if cmd == "yenide":
            tables = self.db.catalog.list_tables()
            if not tables:
                return "Yenu illa macha, full khali."
            return "Tables: " + ", ".join(tables)
        elif cmd == "scene_enu":
            tables_count = len(self.db.catalog.list_tables())
            return (
                "Database: chill macha\n"
                f"Tables: {tables_count}\n"
                "Mood: surviving"
            )
        elif cmd == "full_scene":
            return (
                "CPU: full scene\n"
                "RAM: adjust maadthide\n"
                "Disk: swalpa tension ide\n"
                "Mood: nkn deployment today"
            )
        elif cmd == "sahaaya":
            return "Commands: huttu, huttu_shortcut, haaku, torsu, change_madu, en_kilthya, sutaku, pakka, beda, yenide, scene_enu, full_scene"
        elif cmd == "chill_macha":
            return "Swalpa rest togoni boss. All is well."
        else:
            return f"Gotthilla boss: {cmd}"
            
    def _exec_transaction(self, stmt: TransactionStatement) -> str:
        if stmt.action == "pakka":
            self.db.pakka()
            return "✔ pakka aagide boss"
        elif stmt.action == "beda":
            # For now, rollback just drops all cached dirty pages without saving
            # Real rollback needs WAL.
            self.db.beda()
            return "✔ beda macha, hinde hogona"
        return "Yen action idu?"

    # --- Expression Evaluator ---

    def _eval_expr(self, expr: Expression, row_dict: Dict[str, Any]) -> Any:
        """Evaluate an expression recursively against a row."""
        if isinstance(expr, Literal):
            return expr.value
            
        elif isinstance(expr, ColumnRef):
            if expr.column_name not in row_dict:
                # If evaluating for INSERT/UPDATE where row_dict is empty, this means they used a col ref illegally
                if not row_dict:
                    raise SyntaxBejaarError(f"Cannot use column '{expr.column_name}' here macha.")
                raise ColumnIllaError(expr.column_name)
            return row_dict[expr.column_name]
            
        elif isinstance(expr, BinaryExpr):
            left_val = self._eval_expr(expr.left, row_dict)
            right_val = self._eval_expr(expr.right, row_dict)
            
            # Type casting if mixing int/float
            if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
                pass # Python handles int > float automatically
            elif type(left_val) != type(right_val) and left_val is not None and right_val is not None:
                raise TypeMismatchError("expression", type(left_val).__name__, type(right_val).__name__)
                
            op = expr.operator
            if op == "=": return left_val == right_val
            if op == "!=": return left_val != right_val
            if op == ">": return left_val > right_val
            if op == "<": return left_val < right_val
            if op == ">=": return left_val >= right_val
            if op == "<=": return left_val <= right_val
            
            raise SyntaxBejaarError(f"Unknown operator '{op}' macha.")
            
        raise MachaError("Expression artha aaglilla.")
