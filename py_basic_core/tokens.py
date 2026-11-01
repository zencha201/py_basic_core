"""Token kinds and reserved words (BASIC.md appendix A)."""

from dataclasses import dataclass

INT = "INT"
STRING = "STRING"
IDENT = "IDENT"
KEYWORD = "KEYWORD"
OP = "OP"
LABEL = "LABEL"          # "*NAME" at the start of a line
NEWLINE = "NEWLINE"
EOF = "EOF"

KEYWORDS = frozenset("""
AND DATA DICT DIM ELSE ELSIF END ENDIF ERASE EXIT FOR FUNCTION GLOBAL GOSUB GOTO IF INPUT LET
NEXT NOT OR PRINT READ RESTORE RETURN STEP THEN TO WEND WHILE
""".split())

# Longest first so that "<=" wins over "<".
OPERATORS = ("<>", "<=", ">=", "+", "-", "*", "/", "%", "=", "<", ">", "(", ")", ",", ";", ":")


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    line: int
    column: int = 0

    def is_op(self, value):
        return self.kind == OP and self.value == value

    def is_keyword(self, value):
        return self.kind == KEYWORD and self.value == value

    def ends_statement(self):
        return self.kind in (NEWLINE, EOF) or self.is_op(":")
