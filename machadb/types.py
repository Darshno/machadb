"""
types.py — The Type System of MachaDB

Every database needs types, macha. Ours has two:
  - sankhye (integer) — for counting how many chais you've had
  - pathya (text) — for storing excuses about missed deadlines

We also support float and boolean internally because we're
not *completely* irresponsible. Just mostly.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class DataType(Enum):
    """
    The sacred data types of MachaDB.

    Named in Kannada because SQL keywords are banned, boss.
    """
    SANKHYE = "sankhye"    # INTEGER — signed 64-bit
    PATHYA = "pathya"      # TEXT — UTF-8 string
    DASHAAMSHA = "dashaamsha"  # FLOAT — 64-bit double
    HAAN_ILLA = "haan_illa"    # BOOLEAN — true/false
    KHALI = "khali"        # NULL — nothing, void, emptiness

    @classmethod
    def from_string(cls, s: str) -> "DataType":
        """Parse a type name from a query string, macha."""
        mapping = {
            "sankhye": cls.SANKHYE,
            "pathya": cls.PATHYA,
            "dashaamsha": cls.DASHAAMSHA,
            "haan_illa": cls.HAAN_ILLA,
            "integer": cls.SANKHYE,   # Backup for the English-speaking crowd
            "text": cls.PATHYA,
            "float": cls.DASHAAMSHA,
            "boolean": cls.HAAN_ILLA,
        }
        result = mapping.get(s.lower())
        if result is None:
            raise ValueError(f"ayyo macha, '{s}' is not a valid type. Use sankhye or pathya!")
        return result

    def python_type(self) -> type:
        """What Python type does this map to?"""
        mapping = {
            DataType.SANKHYE: int,
            DataType.PATHYA: str,
            DataType.DASHAAMSHA: float,
            DataType.HAAN_ILLA: bool,
            DataType.KHALI: type(None),
        }
        return mapping[self]


@dataclass
class Column:
    """
    A single column definition in a table schema.

    Like 'id sankhye' or 'hesar pathya'.
    Simple and clean, just like filter coffee.
    """
    name: str
    data_type: DataType
    is_primary_key: bool = False
    is_nullable: bool = True
    default_value: Any = None

    def validate(self, value: Any) -> bool:
        """Check if a value is valid for this column, macha."""
        if value is None:
            return self.is_nullable
        expected = self.data_type.python_type()
        # Allow int values for float columns
        if self.data_type == DataType.DASHAAMSHA and isinstance(value, int):
            return True
        return isinstance(value, expected)

    def to_dict(self) -> dict:
        """Serialize to dict for catalog storage."""
        return {
            "name": self.name,
            "data_type": self.data_type.value,
            "is_primary_key": self.is_primary_key,
            "is_nullable": self.is_nullable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Column":
        """Deserialize from catalog dict."""
        return cls(
            name=data["name"],
            data_type=DataType(data["data_type"]),
            is_primary_key=data.get("is_primary_key", False),
            is_nullable=data.get("is_nullable", True),
        )


@dataclass
class Schema:
    """
    The blueprint of a table — what columns it has and their types.

    Think of it as the assignment specification that nobody reads
    but everyone needs.
    """
    table_name: str
    columns: List[Column] = field(default_factory=list)

    @property
    def column_names(self) -> List[str]:
        """Get all column names in order."""
        return [col.name for col in self.columns]

    @property
    def column_count(self) -> int:
        """How many columns, macha?"""
        return len(self.columns)

    def get_column(self, name: str) -> Optional[Column]:
        """Find a column by name. Returns None if not found (ayyo)."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def get_column_index(self, name: str) -> int:
        """Get the position of a column. Raises if not found."""
        for i, col in enumerate(self.columns):
            if col.name == name:
                return i
        raise ValueError(f"macha, aa column '{name}' ello? Not in table '{self.table_name}'")

    def validate_row(self, values: list) -> bool:
        """Validate a full row of values against this schema."""
        if len(values) != len(self.columns):
            return False
        return all(col.validate(val) for col, val in zip(self.columns, values))

    def to_dict(self) -> dict:
        """Serialize for catalog storage."""
        return {
            "table_name": self.table_name,
            "columns": [col.to_dict() for col in self.columns],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schema":
        """Deserialize from catalog data."""
        return cls(
            table_name=data["table_name"],
            columns=[Column.from_dict(c) for c in data["columns"]],
        )

    def __repr__(self) -> str:
        cols = ", ".join(f"{c.name} {c.data_type.value}" for c in self.columns)
        return f"Schema('{self.table_name}': [{cols}])"
