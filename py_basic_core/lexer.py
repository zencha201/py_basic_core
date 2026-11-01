"""Lexical analysis: source text -> tokens, one source line at a time (DESIGN.md 3)."""

from . import tokens as T
from .errors import SYNTAX_ERROR, UNTERMINATED_STRING, BasicSyntaxError


def is_ident_start(ch):
    return ch.isascii() and (ch.isalpha() or ch == "_")


def is_ident_char(ch):
    return ch.isascii() and (ch.isalnum() or ch == "_")


def tokenize(source, first_line=1):
    """All tokens of ``source``; each line ends with NEWLINE and the list with EOF."""
    result = []
    line_no = first_line
    for line_no, text in enumerate(source.splitlines(), first_line):
        result.extend(tokenize_line(text, line_no))
        result.append(T.Token(T.NEWLINE, None, line_no, len(text)))
    result.append(T.Token(T.EOF, None, line_no + 1 if result else first_line))
    return result


def tokenize_line(text, line_no):
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t　":
            i += 1
            continue
        if ch == "'":
            break
        if ch == "*" and not out and i + 1 < n and is_ident_start(text[i + 1]):
            name, i = _read_name(text, i + 1)
            out.append(T.Token(T.LABEL, name, line_no, i))
            continue
        if ch.isdigit():
            start = i
            while i < n and text[i].isdigit():
                i += 1
            out.append(T.Token(T.INT, int(text[start:i]), line_no, start))
            continue
        if ch == '"':
            value, i = _read_string(text, i, line_no)
            out.append(T.Token(T.STRING, value, line_no, i))
            continue
        if is_ident_start(ch):
            start = i
            name, i = _read_name(text, i)
            if name == "REM":
                break
            kind = T.KEYWORD if name in T.KEYWORDS else T.IDENT
            out.append(T.Token(kind, name, line_no, start))
            continue
        if ch == "?":
            out.append(T.Token(T.KEYWORD, "PRINT", line_no, i))
            i += 1
            continue
        for op in T.OPERATORS:
            if text.startswith(op, i):
                out.append(T.Token(T.OP, op, line_no, i))
                i += len(op)
                break
        else:
            raise BasicSyntaxError(SYNTAX_ERROR, line_no, "'%s'" % ch)
    return out


def _read_name(text, i):
    start = i
    while i < len(text) and is_ident_char(text[i]):
        i += 1
    if i < len(text) and text[i] == "$":
        i += 1
    return text[start:i].upper(), i


def _read_string(text, i, line_no):
    """A string literal starting at text[i] == '"'. A doubled quote stands for one quote."""
    chars = []
    i += 1
    while i < len(text):
        ch = text[i]
        if ch == '"':
            if text.startswith('""', i):
                chars.append('"')
                i += 2
                continue
            return "".join(chars), i + 1
        chars.append(ch)
        i += 1
    raise BasicSyntaxError(UNTERMINATED_STRING, line_no)
