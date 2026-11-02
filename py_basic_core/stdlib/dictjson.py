"""Between DICTs and JSON, for HTTP and DWRITE / DREAD (BASIC.md 6.1 / 6.2).

A DICT is flat (key -> one INT or STRING value). JSON objects and arrays are
flattened into keys joined with "." (a.0.b); the number of elements of an
array is stored under the key "#" (a.#). In the other direction, "." in a key
makes nested objects.
"""

import json
import re

from ..errors import ILLEGAL_FUNCTION_CALL, TYPE_MISMATCH, BasicRuntimeError

COUNT_KEY = "#"                 # number of elements of a JSON array: RES$("items.#")
INT_TEXT = re.compile(r"\s*-?\d+\s*$")


def nest(items):
    """{"a.b": 1} -> {"a": {"b": 1}} (a "." in a key makes a nested object)."""
    root = {}
    for key, value in items:
        parts = key.split(".")
        node = root
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail="key conflict: " + key)
            node = child
        if isinstance(node.get(parts[-1]), dict):
            raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail="key conflict: " + key)
        node[parts[-1]] = value
    return root


def flat_value(value):
    """A JSON value as the string stored in a STRING DICT."""
    if value is None:
        return ""
    if value is True or value is False:
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return str(value)


def int_value(value):
    """A JSON value as the integer stored in an INT DICT (TYPE MISMATCH if it is not a number)."""
    if value is None:
        return 0
    if value is True or value is False:
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)               # toward zero, like "/"
    if isinstance(value, str) and INT_TEXT.match(value):
        return int(value)
    raise BasicRuntimeError(TYPE_MISMATCH, detail="not a number: %r" % value)


def flatten(value, prefix="", convert=flat_value):
    """Parsed JSON -> [(key, value)]: {"a": [{"b": 1}]} -> a.0.b = "1", a.# = "1".

    ``convert`` makes the stored value (flat_value for a STRING DICT, int_value
    for an INT DICT).
    """
    out = []
    if isinstance(value, dict):
        for key, child in value.items():
            out += flatten(child, prefix + str(key) + ".", convert)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            out += flatten(child, prefix + str(i) + ".", convert)
        out.append((prefix + COUNT_KEY, convert(len(value))))
    elif prefix:
        out.append((prefix[:-1], convert(value)))
    return out


def parse_json(text):
    """The parsed JSON object or array, or None when the text is not one."""
    if not text.lstrip()[:1] in ("{", "["):
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None
