"""Instructions of the stack machine that runs BASIC programs (DESIGN.md 5)."""

from dataclasses import dataclass, field

# Values and variables
PUSH = "PUSH"                   # arg: constant
POP = "POP"
LOAD = "LOAD"                   # arg: name
STORE = "STORE"                 # arg: name                 (stack: value)
LOAD_INDEX = "LOAD_INDEX"       # arg: (name, n)            array element or function call
STORE_INDEX = "STORE_INDEX"     # arg: (name, n)            (stack: indices..., value)
DIM = "DIM"                     # arg: (name, n)            (stack: sizes...)
DICT = "DICT"                   # arg: name
ERASE = "ERASE"                 # arg: (name, n)            n = 0: all keys, 1: one key (stack: key)
GLOBAL = "GLOBAL"               # arg: names

# Operators
UNARY = "UNARY"                 # arg: "-", "+", "NOT"
BINARY = "BINARY"               # arg: operator
TRUTH = "TRUTH"                 # top -> 1 / 0
AND_JUMP = "AND_JUMP"           # arg: target. top false -> 0 and jump, else pop
OR_JUMP = "OR_JUMP"             # arg: target. top true -> 1 and jump, else pop

# Control flow
JUMP = "JUMP"                   # arg: target
JUMP_IF_FALSE = "JUMP_IF_FALSE"  # arg: target
FOR_INIT = "FOR_INIT"           # arg: loop id              (stack: end, step)
FOR_CHECK = "FOR_CHECK"         # arg: (loop id, var, exit target)
FOR_STEP = "FOR_STEP"           # arg: (loop id, var, loop top)
FOR_DROP = "FOR_DROP"           # arg: loop id. EXIT FOR / WHILE forgets this loop and the inner ones
GOSUB = "GOSUB"                 # arg: target
RETURN_SUB = "RETURN_SUB"       # RETURN in the main program
RETURN_ANY = "RETURN_ANY"       # RETURN without a value in a function: GOSUB return or function return
RETURN_VALUE = "RETURN_VALUE"   # (stack: value)
CALL = "CALL"                   # arg: (name, n)            function only
END = "END"
EXIT = "EXIT"

# Input / output and extensions
PRINT_VALUE = "PRINT_VALUE"
PRINT_TAB = "PRINT_TAB"
PRINT_NEWLINE = "PRINT_NEWLINE"
INPUT = "INPUT"                 # arg: (prompt, name, n)    (stack: indices...)
READ = "READ"                   # arg: (name, n)            (stack: indices...)
RESTORE = "RESTORE"             # arg: position in the DATA values
COMMAND = "COMMAND"             # arg: (name, n)

JUMP_OPS = frozenset((JUMP, JUMP_IF_FALSE, AND_JUMP, OR_JUMP, GOSUB))


@dataclass
class Instruction:
    op: str
    arg: object
    line: int


@dataclass
class CodeUnit:
    """The code of the main program or of one function."""
    name: str
    instructions: list = field(default_factory=list)
    labels: dict = field(default_factory=dict)              # label -> instruction index
    global_names: frozenset = frozenset()                   # names declared GLOBAL (functions)
