"""Callables: user functions, built-in functions and commands (DESIGN.md 8 / 9)."""

from dataclasses import dataclass
from typing import Callable, Optional

from .errors import ARGUMENT_COUNT, TYPE_MISMATCH, BasicRuntimeError
from .values import check_for_name, expect_int, expect_str
from .variable import BasicDict


@dataclass
class UserFunction:
    name: str
    params: tuple           # basic.ast.Param, ...
    code: object            # basic.code.CodeUnit
    line: int

    @property
    def min_args(self):
        return len(self.params)

    @property
    def max_args(self):
        return len(self.params)


@dataclass
class BuiltinFunction:
    """A function registered from Python: fn(ctx, args) -> int | str."""
    name: str
    fn: Callable
    min_args: int = 0
    max_args: Optional[int] = None


@dataclass
class CommandSpec:
    """A command registered from Python: fn(ctx, args) -> None | Suspend."""
    name: str
    fn: Callable
    min_args: int = 0
    max_args: Optional[int] = None


def check_arg_count(callable_, args):
    n = len(args)
    if n < callable_.min_args or (callable_.max_args is not None and n > callable_.max_args):
        raise BasicRuntimeError(ARGUMENT_COUNT)


def bind_arguments(function, args):
    """Parameter name -> value for a call of a user function.

    The single place where arguments meet parameters, so default and variadic
    parameters (basic.ast.Param) can be added here later.
    """
    check_arg_count(function, args)
    return {p.name: check_for_name(p.name, v) for p, v in zip(function.params, args)}


class Suspend:
    """Returned by a command to pause the program."""


@dataclass
class WaitFrames(Suspend):
    frames: int


class CallContext:
    """What a Python function or command receives besides its arguments."""

    def __init__(self, runtime, name, line):
        self.runtime = runtime
        self.host = runtime.host
        self.name = name
        self.line = line

    def expect_int(self, value):
        return expect_int(value)

    def expect_str(self, value):
        return expect_str(value)

    def expect_dict(self, value):
        """A DICT passed by its bare name: HASKEY(HP, "SLIME")."""
        if not isinstance(value, BasicDict):
            raise BasicRuntimeError(TYPE_MISMATCH, self.line)
        return value

    def error(self, name, detail=""):
        return BasicRuntimeError(name, self.line, detail)
