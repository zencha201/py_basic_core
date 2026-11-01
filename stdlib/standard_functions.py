"""Standard functions (BASIC.md chapter 6), registered with runtime.register_function()."""

import random

from ..errors import ILLEGAL_FUNCTION_CALL
from ..values import parse_int


def abs_function(ctx, args):
    return abs(ctx.expect_int(args[0]))


def min_function(ctx, args):
    return min(ctx.expect_int(v) for v in args)


def max_function(ctx, args):
    return max(ctx.expect_int(v) for v in args)


def len_function(ctx, args):
    return len(ctx.expect_str(args[0]))


def _count(ctx, value):
    n = ctx.expect_int(value)
    if n < 0:
        raise ctx.error(ILLEGAL_FUNCTION_CALL)
    return n


def left_function(ctx, args):
    return ctx.expect_str(args[0])[:_count(ctx, args[1])]


def right_function(ctx, args):
    s = ctx.expect_str(args[0])
    n = _count(ctx, args[1])
    return s[len(s) - n:] if n < len(s) else s


def mid_function(ctx, args):
    """MID$(s$, start[, n]); start counts from 1."""
    s = ctx.expect_str(args[0])
    start = ctx.expect_int(args[1])
    if start < 1:
        raise ctx.error(ILLEGAL_FUNCTION_CALL)
    rest = s[start - 1:]
    return rest[:_count(ctx, args[2])] if len(args) > 2 else rest


def str_function(ctx, args):
    return str(ctx.expect_int(args[0]))


def val_function(ctx, args):
    """Leading sign and digits after any spaces; 0 when there are none."""
    s = ctx.expect_str(args[0]).lstrip()
    end = 1 if s[:1] in ("+", "-") else 0
    while end < len(s) and s[end].isascii() and s[end].isdigit():
        end += 1
    return parse_int(s[:end]) or 0


def rnd_function(ctx, args):
    """RND(n): a random integer from 0 to n-1."""
    n = ctx.expect_int(args[0])
    if n < 1:
        raise ctx.error(ILLEGAL_FUNCTION_CALL)
    return random.randrange(n)


def chr_function(ctx, args):
    n = ctx.expect_int(args[0])
    if not 0 <= n <= 0x10FFFF:
        raise ctx.error(ILLEGAL_FUNCTION_CALL)
    return chr(n)


def asc_function(ctx, args):
    s = ctx.expect_str(args[0])
    if not s:
        raise ctx.error(ILLEGAL_FUNCTION_CALL)
    return ord(s[0])


def instr_function(ctx, args):
    """INSTR(s$, t$): position (from 1) of t$ in s$, 0 when absent."""
    return ctx.expect_str(args[0]).find(ctx.expect_str(args[1])) + 1


def haskey_function(ctx, args):
    """HASKEY(dict, key): 1 when the key is in the DICT."""
    return 1 if ctx.expect_dict(args[0]).has(args[1]) else 0


def count_function(ctx, args):
    """COUNT(dict): number of keys."""
    return ctx.expect_dict(args[0]).count()


def key_function(ctx, args):
    """KEY$(dict, i): the i-th key (from 0) in the order of addition."""
    return ctx.expect_dict(args[0]).key_at(ctx.expect_int(args[1]))


FUNCTIONS = (
    # name, function, min args, max args
    ("ABS", abs_function, 1, 1),
    ("MIN", min_function, 2, None),
    ("MAX", max_function, 2, None),
    ("LEN", len_function, 1, 1),
    ("LEFT$", left_function, 2, 2),
    ("RIGHT$", right_function, 2, 2),
    ("MID$", mid_function, 2, 3),
    ("STR$", str_function, 1, 1),
    ("VAL", val_function, 1, 1),
    ("RND", rnd_function, 1, 1),
    ("CHR$", chr_function, 1, 1),
    ("ASC", asc_function, 1, 1),
    ("INSTR", instr_function, 2, 2),
    ("HASKEY", haskey_function, 2, 2),
    ("COUNT", count_function, 1, 1),
    ("KEY$", key_function, 2, 2),
)


def install(runtime):
    for name, fn, min_args, max_args in FUNCTIONS:
        runtime.register_function(name, fn, min_args, max_args)
