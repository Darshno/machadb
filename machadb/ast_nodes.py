"""
ast_nodes.py — The Abstract Syntax Tree of MachaDB

These classes represent the parsed meaning of our Bengaluru slang queries.
Instead of "SelectStatement", we have "TorsuStatement".

Every node is just a dumb data container, waiting for the
Executor to bring it to life.
"""

from dataclasses import dataclass
from typing import Any, List, Optional
from .types import DataType

# =====================================================================
# Expressions (Things that evaluate to a value)
# =====================================================================

class Expression:
    """Base class for anything that can be evaluated."""
    pass


@dataclass
class Literal(Expression):
    """A hardcoded value: 'Boss', 42, true"""
    value: Any


@dataclass
class ColumnRef(Expression):
    """A reference to a column: hesar, id"""
    column_name: str


@dataclass
class BinaryExpr(Expression):
    """Two things joined by an operator: id = 1, age > 18"""
    left: Expression
    operator: str
    right: Expression


# =====================================================================
# Statements (Commands that DO things)
# =====================================================================

class Statement:
    """Base class for top-level commands."""
    pass


@dataclass
class ColumnDef:
    """A column definition in a CREATE table: id sankhye"""
    name: str
    data_type: DataType


@dataclass
class HuttuStatement(Statement):
    """
    CREATE TABLE
    huttu <table_name> ( <col_defs> )
    """
    table_name: str
    columns: List[ColumnDef]


@dataclass
class HuttuShortcutStatement(Statement):
    """
    CREATE INDEX
    huttu_shortcut <column_name> mele <table_name>
    """
    table_name: str
    column_name: str


@dataclass
class HaakuStatement(Statement):
    """
    INSERT INTO
    haaku <table_name> ( <values> )
    """
    table_name: str
    values: List[Expression]


@dataclass
class TorsuStatement(Statement):
    """
    SELECT
    torsu <columns> <table_name> [elli <where_expr>]
    Note: if columns is empty, it means '*'
    """
    table_name: str
    columns: List[str]  # empty = *
    where_expr: Optional[Expression] = None


@dataclass
class ChangeMaaduStatement(Statement):
    """
    UPDATE
    change_madu <table_name> set <col> = <expr> [elli <where_expr>]
    """
    table_name: str
    set_column: str
    set_value: Expression
    where_expr: Optional[Expression] = None


@dataclass
class EnKilthyaStatement(Statement):
    """
    DELETE
    en_kilthya <table_name> [elli <where_expr>]
    """
    table_name: str
    where_expr: Optional[Expression] = None


@dataclass
class SutakuStatement(Statement):
    """
    DROP TABLE
    sutaku <table_name>
    """
    table_name: str


@dataclass
class TransactionStatement(Statement):
    """
    pakka = COMMIT
    beda = ROLLBACK
    """
    action: str  # "pakka" | "beda" | "begin" (for later)


@dataclass
class SystemStatement(Statement):
    """
    Commands like 'yenide', 'scene_enu', 'full_scene'
    """
    command: str
