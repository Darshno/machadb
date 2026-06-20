"""
artha_maadko.py — The Tokenizer and Parser of MachaDB

'Artha maadko' means 'understand it'. This module reads our beautiful
Bengaluru slang and turns it into AST nodes.

Because SQL regexes are for weaklings, we're doing a proper
recursive-descent parser. Hand-rolled. Chai-fueled.
"""

import re
from typing import List, Optional

from .ast_nodes import (
    Expression, Literal, ColumnRef, BinaryExpr,
    Statement, ColumnDef, HuttuStatement, HuttuShortcutStatement, HaakuStatement,
    TorsuStatement, ChangeMaaduStatement, EnKilthyaStatement,
    SutakuStatement, TransactionStatement, SystemStatement
)
from .types import DataType
from .errors import SyntaxBejaarError


# =====================================================================
# Tokenizer
# =====================================================================

class Token:
    def __init__(self, type_: str, value: str, pos: int):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"


class Tokenizer:
    """Breaks a string into tokens."""

    # We match using regex, but process sequentially
    TOKEN_REGEXES = [
        ("WHITESPACE", r"\s+"),
        ("COMMENT", r"--.*"),
        ("NUMBER", r"-?\d+(\.\d+)?"),
        ("STRING", r"'[^']*'"),
        ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("OPERATOR", r"<=|>=|!=|==|<|>|="),
        ("PUNCTUATION", r"[(),*]"),
    ]
    
    def __init__(self, text: str):
        self.text = text
        self.tokens: List[Token] = []
        self.tokenize()

    def tokenize(self):
        pos = 0
        text_len = len(self.text)
        
        # Combine all regexes into one master regex with named groups
        regex_parts = [f"(?P<{name}>{pattern})" for name, pattern in self.TOKEN_REGEXES]
        master_regex = re.compile("|".join(regex_parts))

        while pos < text_len:
            match = master_regex.match(self.text, pos)
            if not match:
                raise SyntaxBejaarError(f"Idhenu macha? Invalid character at '{self.text[pos:pos+10]}'", pos)
            
            type_ = match.lastgroup
            value = match.group(type_)
            
            if type_ not in ("WHITESPACE", "COMMENT"):
                if type_ == "STRING":
                    # Remove the quotes
                    value = value[1:-1]
                elif type_ == "NUMBER":
                    # Keep as string for now, parse later
                    pass
                elif type_ == "IDENTIFIER":
                    # Case insensitive for identifiers/keywords
                    value = value.lower()
                    
                self.tokens.append(Token(type_, value, pos))
                
            pos = match.end()


# =====================================================================
# Parser
# =====================================================================

class ArthaMaadko:
    """
    The Recursive Descent Parser.
    Reads tokens and builds the AST.
    """
    def __init__(self, text: str):
        self.tokenizer = Tokenizer(text)
        self.tokens = self.tokenizer.tokens
        self.pos = 0

    def parse(self) -> Statement:
        if self._is_at_end():
            raise SyntaxBejaarError("Khali query kottidya macha?")

        token = self._peek()

        if token.value == "huttu":
            return self._parse_huttu()
        elif token.value == "huttu_shortcut":
            return self._parse_huttu_shortcut()
        elif token.value == "haaku":
            return self._parse_haaku()
        elif token.value == "torsu":
            return self._parse_torsu()
        elif token.value == "change_madu":
            return self._parse_change_madu()
        elif token.value == "en_kilthya":
            return self._parse_en_kilthya()
        elif token.value == "sutaku":
            return self._parse_sutaku()
        elif token.value == "pakka":
            self._advance()
            return TransactionStatement("pakka")
        elif token.value == "beda":
            self._advance()
            return TransactionStatement("beda")
        elif token.value in ("yenide", "scene_enu", "full_scene", "sahaaya", "chill_macha", "tea_kudona", "restore_madu"):
            val = self._advance().value
            return SystemStatement(val)
        else:
            raise SyntaxBejaarError(f"Yen command idu? '{token.value}' gotthilla nanage!", token.pos)

    # --- Helpers ---

    def _peek(self) -> Token:
        if self._is_at_end():
            # Return a dummy EOF token to avoid index errors
            return Token("EOF", "", -1)
        return self.tokens[self.pos]

    def _previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def _is_at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.pos += 1
        return self._previous()

    def _match(self, *values) -> bool:
        if self._is_at_end():
            return False
        if self._peek().value in values:
            self._advance()
            return True
        return False
        
    def _consume(self, type_: str, value: Optional[str] = None, error_msg: str = ""):
        if self._is_at_end():
            raise SyntaxBejaarError(error_msg or "Unexpected end of query macha")
        
        token = self._peek()
        if token.type == type_ and (value is None or token.value == value):
            return self._advance()
            
        raise SyntaxBejaarError(error_msg or f"Expected {value or type_}, got '{token.value}'", token.pos)

    def _consume_identifier(self, error_msg: str) -> str:
        token = self._peek()
        if token.type == "IDENTIFIER":
            return self._advance().value
        raise SyntaxBejaarError(error_msg, token.pos)

    # --- Statement Parsers ---

    def _parse_huttu(self) -> HuttuStatement:
        # huttu jana (id sankhye, hesar pathya)
        self._consume("IDENTIFIER", "huttu")
        table_name = self._consume_identifier("Macha, table hesar yenu?")
        
        self._consume("PUNCTUATION", "(", "Bracket haaku boss '('")
        
        columns = []
        while not self._match(")"):
            col_name = self._consume_identifier("Column hesar beku macha")
            type_str = self._consume_identifier("Type yenu boss? (sankhye, pathya, etc)")
            try:
                data_type = DataType.from_string(type_str)
            except ValueError as e:
                raise SyntaxBejaarError(str(e), self._previous().pos)
                
            columns.append(ColumnDef(col_name, data_type))
            
            if not self._match(","):
                if self._peek().value != ")":
                    raise SyntaxBejaarError("Comma hakidya? illandre ')' haaku.", self._peek().pos)
                    
        return HuttuStatement(table_name, columns)

    def _parse_huttu_shortcut(self) -> HuttuShortcutStatement:
        # huttu_shortcut id mele jana
        self._consume("IDENTIFIER", "huttu_shortcut")
        column_name = self._consume_identifier("Yaav column macha?")
        self._consume("IDENTIFIER", "mele", "'mele' beku boss")
        table_name = self._consume_identifier("Yaav table macha?")
        return HuttuShortcutStatement(table_name, column_name)

    def _parse_haaku(self) -> HaakuStatement:
        # haaku jana (1, 'Dheer')
        self._consume("IDENTIFIER", "haaku")
        table_name = self._consume_identifier("Yaav table ge haakbeku?")
        
        self._consume("PUNCTUATION", "(", "Bracket haaku boss '('")
        
        values = []
        while not self._match(")"):
            values.append(self._parse_expression())
            if not self._match(","):
                if self._peek().value != ")":
                    raise SyntaxBejaarError("Comma hakidya? illandre ')' haaku.", self._peek().pos)
                    
        return HaakuStatement(table_name, values)

    def _parse_torsu(self) -> TorsuStatement:
        # torsu * jana elli id = 1
        # or torsu id, hesar jana
        self._consume("IDENTIFIER", "torsu")
        
        columns = []
        if self._match("*"):
            pass # leave columns empty to mean *
        else:
            columns.append(self._consume_identifier("Yen torsbeku? column hesar or '*' kudu"))
            while self._match(","):
                columns.append(self._consume_identifier("Next column hesar kudu"))
                
        table_name = self._consume_identifier("Yaav table inda torsbeku macha?")
        
        where_expr = None
        if self._match("elli"):
            where_expr = self._parse_expression()
            
        return TorsuStatement(table_name, columns, where_expr)

    def _parse_change_madu(self) -> ChangeMaaduStatement:
        # change_madu jana set hesar = 'Boss' elli id = 1
        self._consume("IDENTIFIER", "change_madu")
        table_name = self._consume_identifier("Yaav table macha?")
        
        self._consume("IDENTIFIER", "set", "'set' use maadu boss")
        set_col = self._consume_identifier("Yaav column change madbeku?")
        self._consume("OPERATOR", "=", "'=' haaku")
        
        set_val = self._parse_expression()
        
        where_expr = None
        if self._match("elli"):
            where_expr = self._parse_expression()
            
        return ChangeMaaduStatement(table_name, set_col, set_val, where_expr)

    def _parse_en_kilthya(self) -> EnKilthyaStatement:
        # en_kilthya jana elli id = 1
        self._consume("IDENTIFIER", "en_kilthya")
        table_name = self._consume_identifier("Yaav table macha?")
        
        where_expr = None
        if self._match("elli"):
            where_expr = self._parse_expression()
            
        return EnKilthyaStatement(table_name, where_expr)

    def _parse_sutaku(self) -> SutakuStatement:
        # sutaku jana
        self._consume("IDENTIFIER", "sutaku")
        table_name = self._consume_identifier("Yaav table na suthaakbeku?")
        return SutakuStatement(table_name)

    # --- Expression Parser ---

    def _parse_expression(self) -> Expression:
        # Currently only supporting simple left op right (no complex AND/OR yet to keep it chill)
        left = self._parse_primary()
        
        if self._is_at_end():
            return left
            
        token = self._peek()
        if token.type == "OPERATOR":
            op = self._advance().value
            if op == "==":
                op = "=" # normalize
            right = self._parse_primary()
            return BinaryExpr(left, op, right)
            
        return left

    def _parse_primary(self) -> Expression:
        token = self._advance()
        
        if token.type == "NUMBER":
            if "." in token.value:
                return Literal(float(token.value))
            return Literal(int(token.value))
            
        if token.type == "STRING":
            return Literal(token.value)
            
        if token.type == "IDENTIFIER":
            val = token.value.lower()
            if val == "true" or val == "haan":
                return Literal(True)
            if val == "false" or val == "illa":
                return Literal(False)
            if val == "null" or val == "khali":
                return Literal(None)
            # It's a column reference
            return ColumnRef(val)
            
        raise SyntaxBejaarError(f"Idhenu? value or column name beku, aadhre '{token.value}' kottidya.", token.pos)
