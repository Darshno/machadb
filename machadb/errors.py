"""
errors.py — MachaDB Exception Hierarchy

Every error message sounds like it was written by someone
who just found a bug in production at 3 AM while their
manager is on a Zoom call asking for status updates.

All exceptions inherit from MachaError, so you can catch
everything with a single 'except MachaError' if you're
feeling lazy (we don't judge, boss).
"""


class MachaError(Exception):
    """
    Base exception for all MachaDB errors.
    If you see this, something went wrong, macha.
    """
    pass


class ShataIllaError(MachaError):
    """
    Table not found.
    ayyo macha, aa table illa shata!
    """
    def __init__(self, table_name: str):
        self.table_name = table_name
        super().__init__(f"ayyo macha, '{table_name}' ante yaav table? illa shata!")


class ColumnIllaError(MachaError):
    """
    Column not found.
    macha, aa column ello?
    """
    def __init__(self, column_name: str, table_name: str = ""):
        self.column_name = column_name
        self.table_name = table_name
        ctx = f" in '{table_name}'" if table_name else ""
        super().__init__(f"macha, '{column_name}' column ello{ctx}? Check madu boss.")


class DuplicateError(MachaError):
    """
    Duplicate key / table already exists.
    nkn same item already ide boss!
    """
    def __init__(self, item: str, kind: str = "item"):
        self.item = item
        self.kind = kind
        super().__init__(f"nkn same {kind} '{item}' already ide boss!")


class SyntaxBejaarError(MachaError):
    """
    Syntax error in query.
    nkn correct agi type madu!
    """
    def __init__(self, message: str = "", position: int = -1):
        self.position = position
        prefix = f"(position {position}) " if position >= 0 else ""
        detail = f": {message}" if message else ""
        super().__init__(f"nkn correct agi type madu {prefix}boss{detail}")


class DataUltaError(MachaError):
    """
    Data corruption detected.
    bewarsi, data full ulta aagide!
    """
    def __init__(self, detail: str = ""):
        msg = "bewarsi, data full ulta aagide!"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class GotthillaError(MachaError):
    """
    Unknown / unrecognized command.
    yen heltidya macha?
    """
    def __init__(self, command: str = ""):
        if command:
            super().__init__(f"yen heltidya macha? '{command}' gotthilla nanage!")
        else:
            super().__init__("yen heltidya macha? artha aagthilla!")


class TypeMismatchError(MachaError):
    """
    Wrong data type for a column.
    macha, type match aagthilla!
    """
    def __init__(self, column: str, expected: str, got: str):
        self.column = column
        self.expected = expected
        self.got = got
        super().__init__(
            f"macha, '{column}' ge {expected} beku, but neevu {got} kottidira! "
            f"type check madu boss."
        )


class PageFullError(MachaError):
    """
    No space left in the page.
    ayyo, page full aagide macha!
    """
    def __init__(self, page_id: int = -1):
        ctx = f" (page {page_id})" if page_id >= 0 else ""
        super().__init__(f"ayyo, page full aagide{ctx}! Jagah illa macha!")


class TransactionError(MachaError):
    """
    Transaction-related error.
    transaction alli problem aagide boss!
    """
    def __init__(self, detail: str = ""):
        msg = "transaction alli problem aagide boss!"
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class FileCorruptError(MachaError):
    """
    Database file is corrupt.
    file corrupt aagide macha, yaardhru touch maadidra?
    """
    def __init__(self, filename: str = "", detail: str = ""):
        msg = f"file corrupt aagide macha"
        if filename:
            msg += f" ({filename})"
        msg += "! yaardhru touch maadidra?"
        if detail:
            msg += f" [{detail}]"
        super().__init__(msg)
