"""AST nodes (DESIGN.md 4). Every node keeps the source line it came from.

The module is not called ``ast`` so that it never hides the standard library
module of that name when the core folder itself is on ``sys.path``.
"""

from dataclasses import dataclass, field
from typing import Optional


# --- expressions -------------------------------------------------------------
@dataclass(frozen=True)
class IntLiteral:
    value: int
    line: int


@dataclass(frozen=True)
class StringLiteral:
    value: str
    line: int


@dataclass(frozen=True)
class Name:
    """A plain variable reference: ``A``, ``NAME$``."""
    name: str
    line: int


@dataclass(frozen=True)
class CallOrIndex:
    """``NAME(args)``: an array element or a function call, decided at run time (BASIC.md 5.5)."""
    name: str
    args: tuple
    line: int


@dataclass(frozen=True)
class Unary:
    op: str             # "-", "+", "NOT"
    operand: object
    line: int


@dataclass(frozen=True)
class Binary:
    op: str             # "+", "-", "*", "/", "%", "=", "<>", "<", "<=", ">", ">=", "AND", "OR"
    left: object
    right: object
    line: int


# --- statements --------------------------------------------------------------
@dataclass(frozen=True)
class Assign:
    target: object      # Name or CallOrIndex (array element)
    value: object
    line: int


@dataclass(frozen=True)
class PrintItem:
    expr: Optional[object]
    separator: Optional[str]    # ";", "," or None (last item without a separator)


@dataclass(frozen=True)
class Print:
    items: tuple
    line: int


@dataclass(frozen=True)
class Input:
    prompt: Optional[str]
    target: object      # Name or CallOrIndex
    line: int


@dataclass(frozen=True)
class If:
    branches: tuple     # ((condition, body), ...) for IF and each ELSIF
    else_body: Optional[tuple]
    line: int


@dataclass(frozen=True)
class For:
    var: str
    start: object
    end: object
    step: Optional[object]
    body: tuple
    line: int


@dataclass(frozen=True)
class While:
    condition: object
    body: tuple
    line: int


@dataclass(frozen=True)
class Label:
    name: str
    line: int


@dataclass(frozen=True)
class Goto:
    label: str
    line: int


@dataclass(frozen=True)
class Gosub:
    label: str
    line: int


@dataclass(frozen=True)
class Return:
    value: Optional[object]
    line: int


@dataclass(frozen=True)
class End:
    line: int


@dataclass(frozen=True)
class Exit:
    """Leaves direct mode (BASIC.md 8.2)."""
    line: int


@dataclass(frozen=True)
class ExitLoop:
    """``EXIT FOR`` / ``EXIT WHILE``: leave the innermost loop of that kind (BASIC.md 4.6 / 4.7)."""
    kind: str           # "FOR" or "WHILE"
    line: int


@dataclass(frozen=True)
class ContinueLoop:
    """``CONTINUE`` / ``CONTINUE FOR`` / ``CONTINUE WHILE``: go on with the next round (BASIC.md 4.7.2)."""
    kind: Optional[str]     # "FOR", "WHILE", or None for the innermost loop
    line: int


@dataclass(frozen=True)
class CaseItem:
    """One test of a CASE: ``= a``, ``a TO b`` or ``IS op a``."""
    kind: str               # "=", "TO" or a comparison operator for IS
    first: object
    last: Optional[object] = None


@dataclass(frozen=True)
class Select:
    """``SELECT CASE`` (BASIC.md 4.15)."""
    selector: object
    cases: tuple            # ((items, body), ...)
    else_body: Optional[tuple]
    line: int


@dataclass(frozen=True)
class OnError:
    """``ON ERROR GOTO / GOSUB label``, or ``ON ERROR GOTO 0`` (kind None) (BASIC.md 4.16)."""
    kind: Optional[str]     # "GOTO", "GOSUB" or None
    label: Optional[str]
    line: int


@dataclass(frozen=True)
class ArrayDecl:
    name: str
    sizes: tuple        # one expression per dimension (1 or 2)


@dataclass(frozen=True)
class Dim:
    arrays: tuple       # ArrayDecl, ...
    line: int


@dataclass(frozen=True)
class DictDecl:
    """``DICT HP, JOB$``: associative arrays (BASIC.md 4.14)."""
    names: tuple
    line: int


@dataclass(frozen=True)
class Erase:
    """``ERASE HP("SLIME")`` removes one key, ``ERASE HP`` removes all."""
    targets: tuple      # Name or CallOrIndex with one key, ...
    line: int


@dataclass(frozen=True)
class Global:
    names: tuple
    line: int


@dataclass(frozen=True)
class Data:
    """``DATA 1, -2, "A"``: values for READ, never executed (BASIC.md 4.13)."""
    values: tuple
    line: int


@dataclass(frozen=True)
class Read:
    targets: tuple      # Name or CallOrIndex, ...
    line: int


@dataclass(frozen=True)
class Restore:
    label: Optional[str]    # None: back to the first DATA
    line: int


@dataclass(frozen=True)
class Command:
    """A statement registered from Python: ``CLS 0``."""
    name: str
    args: tuple
    line: int


@dataclass(frozen=True)
class CallStatement:
    """A user / built-in function called for its effect: ``ADD_SCORE(10)``."""
    name: str
    args: tuple
    line: int


# --- definitions -------------------------------------------------------------
@dataclass(frozen=True)
class Param:
    """A function parameter. ``default`` and ``variadic`` are reserved for later (DESIGN.md 9)."""
    name: str
    default: Optional[object] = None
    variadic: bool = False


@dataclass(frozen=True)
class FunctionDef:
    name: str
    params: tuple       # Param, ...
    body: tuple
    line: int


@dataclass
class Program:
    body: list = field(default_factory=list)
    functions: list = field(default_factory=list)
