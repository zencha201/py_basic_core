"""The table of commands and built-in functions added from Python (DESIGN.md 8)."""

from .function import BuiltinFunction, CommandSpec
from .lexer import is_ident_char, is_ident_start
from .tokens import KEYWORDS


def normalize_name(name):
    upper = name.upper()
    body = upper[:-1] if upper.endswith("$") else upper
    if not body or not is_ident_start(body[0]) or not all(is_ident_char(c) for c in body):
        raise ValueError("not a BASIC name: %r" % name)
    if upper in KEYWORDS:
        raise ValueError("reserved word: %r" % name)
    return upper


class Registry:
    def __init__(self):
        self.functions = {}
        self.commands = {}

    def register_function(self, name, fn, min_args=0, max_args=None):
        name = normalize_name(name)
        self.functions[name] = BuiltinFunction(name, fn, min_args, max_args)

    def register_command(self, name, fn, min_args=0, max_args=None):
        name = normalize_name(name)
        self.commands[name] = CommandSpec(name, fn, min_args, max_args)

    def command_names(self):
        return frozenset(self.commands)
