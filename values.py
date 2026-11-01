"""The two value types, INT and STRING (BASIC.md chapter 2).

A DICT itself can also be on the stack (a bare DICT name, BASIC.md 4.14),
but only functions that ask for one with expect_dict accept it.
"""

from .errors import TYPE_MISMATCH, BasicRuntimeError

INT = "INT"
STRING = "STRING"


def is_string_name(name):
    """Names ending in "$" hold strings; all others hold integers."""
    return name.endswith("$")


def default_for(name):
    return "" if is_string_name(name) else 0


def type_of(value):
    return STRING if isinstance(value, str) else INT


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def check_value(value):
    """Raise TYPE MISMATCH unless ``value`` is an INT or a STRING."""
    if not (is_int(value) or isinstance(value, str)):
        raise BasicRuntimeError(TYPE_MISMATCH)
    return value


def check_for_name(name, value):
    """Raise TYPE MISMATCH unless ``value`` may be stored in (or returned by) ``name``."""
    if isinstance(value, str) != is_string_name(name) or not (is_int(value) or isinstance(value, str)):
        raise BasicRuntimeError(TYPE_MISMATCH)
    return value


def expect_int(value):
    if not is_int(value):
        raise BasicRuntimeError(TYPE_MISMATCH)
    return value


def expect_str(value):
    if not isinstance(value, str):
        raise BasicRuntimeError(TYPE_MISMATCH)
    return value


def to_text(value):
    """How PRINT shows a value."""
    return value if isinstance(value, str) else str(value)


def parse_int(text):
    """Integer typed at INPUT. Empty input is 0; anything else invalid gives None."""
    text = text.strip()
    if text == "":
        return 0
    body = text[1:] if text[0] in "+-" else text
    if not body.isascii() or not body.isdigit():
        return None
    return int(text)
