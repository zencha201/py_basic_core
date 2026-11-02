"""Errors raised by the BASIC core (BASIC.md chapter 9)."""

# Syntax errors (found before running)
SYNTAX_ERROR = "SYNTAX ERROR"
UNDEFINED_LABEL = "UNDEFINED LABEL"
DUPLICATE_LABEL = "DUPLICATE LABEL"
DUPLICATE_FUNCTION = "DUPLICATE FUNCTION"
UNTERMINATED_STRING = "UNTERMINATED STRING"
NOT_IN_DIRECT_MODE = "NOT ALLOWED IN DIRECT MODE"

# Runtime errors
TYPE_MISMATCH = "TYPE MISMATCH"
DIVISION_BY_ZERO = "DIVISION BY ZERO"
SUBSCRIPT_OUT_OF_RANGE = "SUBSCRIPT OUT OF RANGE"
UNDEFINED_ARRAY = "UNDEFINED ARRAY"
UNDEFINED_FUNCTION = "UNDEFINED FUNCTION"
ARGUMENT_COUNT = "ARGUMENT COUNT MISMATCH"
ILLEGAL_FUNCTION_CALL = "ILLEGAL FUNCTION CALL"
REDIM = "REDIM"
STACK_OVERFLOW = "STACK OVERFLOW"
RETURN_WITHOUT_GOSUB = "RETURN WITHOUT GOSUB"
NEXT_WITHOUT_FOR = "NEXT WITHOUT FOR"
STEP_IS_ZERO = "STEP IS ZERO"
NAME_CONFLICT = "ARRAY AND VARIABLE NAME CONFLICT"
FILE_NOT_FOUND = "FILE NOT FOUND"
OUT_OF_DATA = "OUT OF DATA"
NETWORK_ERROR = "NETWORK ERROR"


class BasicError(Exception):
    """An error with its BASIC name (e.g. "TYPE MISMATCH") and source line (1-based)."""

    def __init__(self, name, line=None, detail=""):
        super().__init__(name)
        self.name = name
        self.line = line
        self.detail = detail

    def message(self, with_line=True):
        text = "?" + self.name
        if self.detail:
            text += " (" + self.detail + ")"
        if with_line and self.line is not None:
            text += " IN %d" % self.line
        return text

    def __str__(self):
        return self.message()


class BasicSyntaxError(BasicError):
    pass


class BasicRuntimeError(BasicError):
    pass
