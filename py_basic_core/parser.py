"""Syntax analysis: tokens -> AST (DESIGN.md 4, grammar in BASIC.md appendix B).

Expressions are parsed by recursive descent. Statements are read as a stream
separated by ":" and line ends; block structures (IF / FOR / WHILE / FUNCTION)
are matched by reading nested blocks until their closing keyword.
"""

from . import nodes
from . import tokens as T
from .errors import NOT_IN_DIRECT_MODE, SYNTAX_ERROR, BasicSyntaxError

# Closing keywords of blocks, as returned by Parser._terminator().
ELSE = "ELSE"
ELSIF = "ELSIF"
ENDIF = "ENDIF"
NEXT = "NEXT"
WEND = "WEND"
END_FUNCTION = "END FUNCTION"

# Error for a closing keyword that does not close the current block.
STRAY_TERMINATOR = {
    ELSE: "ELSE WITHOUT IF",
    ELSIF: "ELSIF WITHOUT IF",
    ENDIF: "ENDIF WITHOUT IF",
    NEXT: "NEXT WITHOUT FOR",
    WEND: "WEND WITHOUT WHILE",
    END_FUNCTION: "END FUNCTION WITHOUT FUNCTION",
}

COMPARISON_OPS = ("=", "<>", "<", "<=", ">", ">=")
MAX_DIMENSIONS = 2


def parse(tokens, command_names=(), direct_mode=False):
    return Parser(tokens, command_names, direct_mode).parse_program()


class Parser:
    def __init__(self, tokens, command_names=(), direct_mode=False):
        self.tokens = tokens
        self.pos = 0
        self.command_names = frozenset(command_names)
        self.direct_mode = direct_mode
        self.in_function = False
        self.program = nodes.Program()

    # --- token helpers -----------------------------------------------------
    def peek(self, offset=0):
        i = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[i]

    def next(self):
        tok = self.peek()
        self.pos = min(self.pos + 1, len(self.tokens) - 1)
        return tok

    def error(self, detail="", tok=None, name=SYNTAX_ERROR):
        return BasicSyntaxError(name, (tok or self.peek()).line, detail)

    def accept_op(self, value):
        if self.peek().is_op(value):
            return self.next()
        return None

    def accept_keyword(self, value):
        if self.peek().is_keyword(value):
            return self.next()
        return None

    def expect_op(self, value):
        tok = self.accept_op(value)
        if tok is None:
            raise self.error("'%s' expected" % value)
        return tok

    def expect_keyword(self, value):
        tok = self.accept_keyword(value)
        if tok is None:
            raise self.error("%s expected" % value)
        return tok

    def expect_ident(self):
        tok = self.peek()
        if tok.kind != T.IDENT:
            raise self.error("name expected")
        return self.next().value

    def at_inline_end(self):
        """End of a statement inside a one-line IF (ELSE also ends it)."""
        tok = self.peek()
        return tok.ends_statement() or tok.is_keyword("ELSE")

    # --- program and blocks --------------------------------------------------
    def parse_program(self):
        self.program.body = self.block(())
        return self.program

    def block(self, terminators, opener=None, inline=False, top_level=True):
        """Statements up to (not including) one of ``terminators``.

        opener: (error name, line) reported when the block is never closed.
        inline: the block lives inside a one-line IF and must end on this line.
        """
        body = []
        while True:
            self.skip_separators(inline)
            tok = self.peek()
            if tok.kind == T.EOF or (inline and tok.kind == T.NEWLINE):
                if terminators:
                    raise BasicSyntaxError(opener[0], opener[1])
                return body
            term = self.terminator()
            if term is not None:
                if term in terminators:
                    return body
                raise self.error(name=STRAY_TERMINATOR[term])
            if tok.kind == T.LABEL:
                self.next()
                body.append(nodes.Label(tok.value, tok.line))
                continue
            if tok.is_keyword("FUNCTION"):
                if self.direct_mode:
                    raise self.error(name=NOT_IN_DIRECT_MODE)
                if not top_level or inline:
                    raise self.error("FUNCTION inside a block")
                self.program.functions.append(self.function_def())
                continue
            body.append(self.statement(inline))
            if not self.peek().ends_statement() and not (inline and self.peek().is_keyword("ELSE")):
                raise self.error()

    def skip_separators(self, inline):
        while True:
            if self.accept_op(":"):
                continue
            if not inline and self.peek().kind == T.NEWLINE:
                self.next()
                continue
            return

    def terminator(self):
        tok = self.peek()
        if tok.kind != T.KEYWORD:
            return None
        if tok.value in (ELSE, ELSIF, ENDIF, NEXT, WEND):
            return tok.value
        if tok.value == "END":
            following = self.peek(1)
            if following.is_keyword("IF"):
                return ENDIF
            if following.is_keyword("FUNCTION"):
                return END_FUNCTION
        return None

    def consume_terminator(self, term):
        if self.next().value == "END":     # "END IF" / "END FUNCTION"
            self.next()
        if term == NEXT and self.peek().kind == T.IDENT:
            self.next()                    # NEXT I: the variable name is ignored

    def inline_statements(self):
        """Statements after THEN / ELSE of a one-line IF, up to ELSE or the line end."""
        body = [self.statement(inline=True)]
        while self.accept_op(":"):
            if self.at_inline_end():
                break
            body.append(self.statement(inline=True))
        if not self.at_inline_end():
            raise self.error()
        return tuple(body)

    # --- statements ----------------------------------------------------------
    def statement(self, inline=False):
        tok = self.peek()
        if tok.kind == T.KEYWORD:
            handler = self.KEYWORD_STATEMENTS.get(tok.value)
            if handler is None:
                raise self.error()
            return handler(self, inline)
        if tok.kind == T.IDENT:
            if tok.value in self.command_names:
                return self.command()
            return self.assign_or_call()
        raise self.error()

    def print_statement(self, inline):
        line = self.next().line
        items = []
        while not self.at_inline_end():
            expr = self.expr()
            sep = None
            for s in (";", ","):
                if self.accept_op(s):
                    sep = s
                    break
            items.append(nodes.PrintItem(expr, sep))
            if sep is None:
                break
        return nodes.Print(tuple(items), line)

    def input_statement(self, inline):
        line = self.next().line
        prompt = None
        if self.peek().kind == T.STRING:
            prompt = self.next().value
            if not (self.accept_op(";") or self.accept_op(",")):
                raise self.error("';' expected")
        return nodes.Input(prompt, self.lvalue(), line)

    def if_statement(self, inline):
        line = self.next().line
        cond = self.expr()
        has_then = self.accept_keyword("THEN") is not None
        if self.peek().ends_statement():
            if inline:
                raise self.error("block IF inside a one-line IF")
            return self.block_if(cond, line)
        if not has_then:
            raise self.error("THEN expected")
        then_body = self.inline_statements()
        else_body = None
        if self.accept_keyword("ELSE"):
            else_body = self.inline_statements()
        return nodes.If(((cond, then_body),), else_body, line)

    def block_if(self, cond, line):
        opener = ("IF WITHOUT ENDIF", line)
        branches = [(cond, tuple(self.block((ELSIF, ELSE, ENDIF), opener, top_level=False)))]
        else_body = None
        while True:
            term = self.terminator()
            self.consume_terminator(term)
            if term == ELSIF:
                c = self.expr()
                self.accept_keyword("THEN")
                branches.append((c, tuple(self.block((ELSIF, ELSE, ENDIF), opener, top_level=False))))
            elif term == ELSE:
                else_body = tuple(self.block((ENDIF,), opener, top_level=False))
            else:
                return nodes.If(tuple(branches), else_body, line)

    def for_statement(self, inline):
        line = self.next().line
        var = self.expect_ident()
        self.expect_op("=")
        start = self.expr()
        self.expect_keyword("TO")
        end = self.expr()
        step = self.expr() if self.accept_keyword("STEP") else None
        body = self.block((NEXT,), ("FOR WITHOUT NEXT", line), inline, top_level=False)
        self.consume_terminator(NEXT)
        return nodes.For(var, start, end, step, tuple(body), line)

    def while_statement(self, inline):
        line = self.next().line
        cond = self.expr()
        body = self.block((WEND,), ("WHILE WITHOUT WEND", line), inline, top_level=False)
        self.consume_terminator(WEND)
        return nodes.While(cond, tuple(body), line)

    def label_name(self):
        self.accept_op("*")
        tok = self.peek()
        if tok.kind not in (T.IDENT, T.KEYWORD):
            raise self.error("label expected")
        return self.next().value

    def goto_statement(self, inline):
        line = self.next().line
        return nodes.Goto(self.label_name(), line)

    def gosub_statement(self, inline):
        line = self.next().line
        return nodes.Gosub(self.label_name(), line)

    def return_statement(self, inline):
        line = self.next().line
        value = None if self.at_inline_end() else self.expr()
        return nodes.Return(value, line)

    def end_statement(self, inline):
        return nodes.End(self.next().line)

    def exit_statement(self, inline):
        tok = self.next()
        for kind in ("FOR", "WHILE"):
            if self.accept_keyword(kind):
                return nodes.ExitLoop(kind, tok.line)
        if not self.direct_mode:
            raise self.error("EXIT is for direct mode", tok)
        return nodes.Exit(tok.line)

    def dim_statement(self, inline):
        line = self.next().line
        arrays = []
        while True:
            name = self.expect_ident()
            sizes = self.arguments()
            if not 1 <= len(sizes) <= MAX_DIMENSIONS:
                raise self.error("1 or 2 dimensions")
            arrays.append(nodes.ArrayDecl(name, sizes))
            if not self.accept_op(","):
                return nodes.Dim(tuple(arrays), line)

    def dict_statement(self, inline):
        line = self.next().line
        names = [self.expect_ident()]
        while self.accept_op(","):
            names.append(self.expect_ident())
        return nodes.DictDecl(tuple(names), line)

    def erase_statement(self, inline):
        line = self.next().line
        targets = [self.erase_target()]
        while self.accept_op(","):
            targets.append(self.erase_target())
        return nodes.Erase(tuple(targets), line)

    def erase_target(self):
        tok = self.peek()
        target = self.lvalue()
        if isinstance(target, nodes.CallOrIndex) and len(target.args) != 1:
            raise self.error("one key", tok)
        return target

    def global_statement(self, inline):
        tok = self.next()
        if not self.in_function:
            raise self.error("GLOBAL outside FUNCTION", tok)
        names = [self.expect_ident()]
        while self.accept_op(","):
            names.append(self.expect_ident())
        return nodes.Global(tuple(names), tok.line)

    def let_statement(self, inline):
        self.next()
        if self.peek().kind != T.IDENT:
            raise self.error("name expected")
        return self.assign_or_call(require_assign=True)

    def data_statement(self, inline):
        tok = self.next()
        if self.in_function:
            raise self.error("DATA inside FUNCTION", tok)
        values = [self.data_value()]
        while self.accept_op(","):
            values.append(self.data_value())
        return nodes.Data(tuple(values), tok.line)

    def data_value(self):
        """A literal: an integer (optionally signed) or a string."""
        tok = self.peek()
        if tok.kind == T.STRING:
            return self.next().value
        sign = 1
        if tok.kind == T.OP and tok.value in ("-", "+"):
            sign = -1 if self.next().value == "-" else 1
        if self.peek().kind != T.INT:
            raise self.error("number or string expected")
        return sign * self.next().value

    def read_statement(self, inline):
        line = self.next().line
        targets = [self.lvalue()]
        while self.accept_op(","):
            targets.append(self.lvalue())
        return nodes.Read(tuple(targets), line)

    def restore_statement(self, inline):
        line = self.next().line
        label = None if self.at_inline_end() else self.label_name()
        return nodes.Restore(label, line)

    def command(self):
        tok = self.next()
        args = []
        if not self.at_inline_end():
            args.append(self.expr())
            while self.accept_op(","):
                args.append(self.expr())
        return nodes.Command(tok.value, tuple(args), tok.line)

    def assign_or_call(self, require_assign=False):
        tok = self.next()
        name = tok.value
        if self.peek().is_op("("):
            args = self.arguments()
            if self.accept_op("="):
                if not 1 <= len(args) <= MAX_DIMENSIONS:
                    raise self.error("1 or 2 subscripts", tok)
                return nodes.Assign(nodes.CallOrIndex(name, args, tok.line), self.expr(), tok.line)
            if require_assign:
                raise self.error("'=' expected")
            return nodes.CallStatement(name, args, tok.line)
        self.expect_op("=")
        return nodes.Assign(nodes.Name(name, tok.line), self.expr(), tok.line)

    def lvalue(self):
        tok = self.peek()
        name = self.expect_ident()
        if self.peek().is_op("("):
            args = self.arguments()
            if not 1 <= len(args) <= MAX_DIMENSIONS:
                raise self.error("1 or 2 subscripts", tok)
            return nodes.CallOrIndex(name, args, tok.line)
        return nodes.Name(name, tok.line)

    KEYWORD_STATEMENTS = {
        "PRINT": print_statement,
        "INPUT": input_statement,
        "IF": if_statement,
        "FOR": for_statement,
        "WHILE": while_statement,
        "GOTO": goto_statement,
        "GOSUB": gosub_statement,
        "RETURN": return_statement,
        "END": end_statement,
        "EXIT": exit_statement,
        "DIM": dim_statement,
        "DICT": dict_statement,
        "ERASE": erase_statement,
        "GLOBAL": global_statement,
        "LET": let_statement,
        "DATA": data_statement,
        "READ": read_statement,
        "RESTORE": restore_statement,
    }

    # --- functions -----------------------------------------------------------
    def function_def(self):
        line = self.next().line
        name = self.expect_ident()
        self.expect_op("(")
        params = []
        if not self.peek().is_op(")"):
            while True:
                pname = self.expect_ident()
                if any(p.name == pname for p in params):
                    raise self.error("duplicate parameter " + pname)
                params.append(nodes.Param(pname))
                if not self.accept_op(","):
                    break
        self.expect_op(")")
        if not self.peek().ends_statement():
            raise self.error()
        self.in_function = True
        body = self.block((END_FUNCTION,), ("FUNCTION WITHOUT END FUNCTION", line), top_level=False)
        self.in_function = False
        self.consume_terminator(END_FUNCTION)
        return nodes.FunctionDef(name, tuple(params), tuple(body), line)

    # --- expressions ---------------------------------------------------------
    def expr(self):
        return self.or_expr()

    def or_expr(self):
        left = self.and_expr()
        while self.peek().is_keyword("OR"):
            line = self.next().line
            left = nodes.Binary("OR", left, self.and_expr(), line)
        return left

    def and_expr(self):
        left = self.not_expr()
        while self.peek().is_keyword("AND"):
            line = self.next().line
            left = nodes.Binary("AND", left, self.not_expr(), line)
        return left

    def not_expr(self):
        if self.peek().is_keyword("NOT"):
            line = self.next().line
            return nodes.Unary("NOT", self.not_expr(), line)
        return self.comparison()

    def comparison(self):
        left = self.additive()
        while self.peek().kind == T.OP and self.peek().value in COMPARISON_OPS:
            tok = self.next()
            left = nodes.Binary(tok.value, left, self.additive(), tok.line)
        return left

    def additive(self):
        left = self.term()
        while self.peek().kind == T.OP and self.peek().value in ("+", "-"):
            tok = self.next()
            left = nodes.Binary(tok.value, left, self.term(), tok.line)
        return left

    def term(self):
        left = self.unary()
        while self.peek().kind == T.OP and self.peek().value in ("*", "/", "%"):
            tok = self.next()
            left = nodes.Binary(tok.value, left, self.unary(), tok.line)
        return left

    def unary(self):
        tok = self.peek()
        if tok.kind == T.OP and tok.value in ("-", "+"):
            self.next()
            return nodes.Unary(tok.value, self.unary(), tok.line)
        return self.primary()

    def primary(self):
        tok = self.peek()
        if tok.kind == T.INT:
            self.next()
            return nodes.IntLiteral(tok.value, tok.line)
        if tok.kind == T.STRING:
            self.next()
            return nodes.StringLiteral(tok.value, tok.line)
        if tok.kind == T.IDENT:
            self.next()
            if self.peek().is_op("("):
                return nodes.CallOrIndex(tok.value, self.arguments(), tok.line)
            return nodes.Name(tok.value, tok.line)
        if tok.is_op("("):
            self.next()
            inner = self.expr()
            self.expect_op(")")
            return inner
        raise self.error("expression expected")

    def arguments(self):
        """'(' [expr {',' expr}] ')'"""
        self.expect_op("(")
        args = []
        if not self.peek().is_op(")"):
            args.append(self.expr())
            while self.accept_op(","):
                args.append(self.expr())
        self.expect_op(")")
        return tuple(args)
