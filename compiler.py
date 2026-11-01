"""AST -> instructions of the stack machine (DESIGN.md 5).

The main program and each function become separate CodeUnits. All function
definitions are collected before anything runs, so functions may be called
before they are defined.
"""

from dataclasses import dataclass

from . import nodes
from . import instructions as C
from .instructions import CodeUnit, Instruction
from .errors import (DUPLICATE_FUNCTION, DUPLICATE_LABEL, SYNTAX_ERROR, UNDEFINED_LABEL,
                     BasicSyntaxError)
from .function import UserFunction


@dataclass
class CompiledProgram:
    main: CodeUnit
    functions: dict         # name -> UserFunction
    data: tuple             # values of all DATA statements, in source order


class DataPool:
    """DATA values of the main program and where each label falls among them (for RESTORE)."""

    def __init__(self):
        self.values = []
        self.label_positions = {}
        self.restore_refs = []      # (instruction, label name)

    def resolve(self):
        for ins, label in self.restore_refs:
            if label not in self.label_positions:
                raise BasicSyntaxError(UNDEFINED_LABEL, ins.line, label)
            ins.arg = self.label_positions[label]


def compile_program(program):
    data = DataPool()
    main = UnitCompiler("main", in_function=False, data=data).compile(
        program.body, end_line=last_line(program))
    functions = {}
    for fdef in program.functions:
        if fdef.name in functions:
            raise BasicSyntaxError(DUPLICATE_FUNCTION, fdef.line, fdef.name)
        functions[fdef.name] = compile_function(fdef, data)
    data.resolve()
    return CompiledProgram(main, functions, tuple(data.values))


def compile_function(fdef, data):
    params = {p.name for p in fdef.params}
    global_names = set()
    for stmt in walk(fdef.body):
        if isinstance(stmt, nodes.Global):
            for name in stmt.names:
                if name in params:
                    raise BasicSyntaxError(SYNTAX_ERROR, stmt.line, "GLOBAL of parameter " + name)
                global_names.add(name)
    unit = UnitCompiler(fdef.name, in_function=True, global_names=frozenset(global_names), data=data)
    code = unit.compile(fdef.body, end_line=fdef.line)
    return UserFunction(fdef.name, fdef.params, code, fdef.line)


def walk(body):
    """Every statement in ``body``, including those nested in blocks."""
    for stmt in body:
        yield stmt
        if isinstance(stmt, nodes.If):
            for _, branch in stmt.branches:
                yield from walk(branch)
            if stmt.else_body:
                yield from walk(stmt.else_body)
        elif isinstance(stmt, (nodes.For, nodes.While)):
            yield from walk(stmt.body)


def last_line(program):
    lines = [s.line for s in program.body]
    return max(lines) if lines else 1


@dataclass
class OpenLoop:
    """A FOR / WHILE being compiled, for EXIT FOR / EXIT WHILE."""
    kind: str               # "FOR" or "WHILE"
    loop_id: int            # FOR only (0 for WHILE)
    exits: list             # JUMP instructions to patch with the loop's end


class UnitCompiler:
    def __init__(self, name, in_function, global_names=frozenset(), data=None):
        self.unit = CodeUnit(name, global_names=global_names)
        self.in_function = in_function
        self.data = data if data is not None else DataPool()
        self.label_refs = []        # (instruction, label name)
        self.loop_count = 0
        self.loops = []             # enclosing loops while compiling: OpenLoop, innermost last

    # --- helpers -------------------------------------------------------------
    def emit(self, op, arg=None, line=0):
        ins = Instruction(op, arg, line)
        self.unit.instructions.append(ins)
        return ins

    def here(self):
        return len(self.unit.instructions)

    def emit_to_label(self, op, label, line):
        self.label_refs.append((self.emit(op, None, line), label))

    def compile(self, body, end_line):
        self.block(body)
        if self.in_function:
            self.emit(C.RETURN_ANY, None, end_line)
        else:
            self.emit(C.END, None, end_line)
        for ins, label in self.label_refs:
            if label not in self.unit.labels:
                raise BasicSyntaxError(UNDEFINED_LABEL, ins.line, label)
            ins.arg = self.unit.labels[label]
        return self.unit

    def block(self, body):
        for stmt in body:
            self.STATEMENTS[type(stmt)](self, stmt)

    # --- statements ----------------------------------------------------------
    def label(self, s):
        if s.name in self.unit.labels:
            raise BasicSyntaxError(DUPLICATE_LABEL, s.line, s.name)
        self.unit.labels[s.name] = self.here()
        if not self.in_function:
            self.data.label_positions[s.name] = len(self.data.values)

    def assign(self, s):
        target = s.target
        if isinstance(target, nodes.Name):
            self.expr(s.value)
            self.emit(C.STORE, target.name, s.line)
        else:
            for index in target.args:
                self.expr(index)
            self.expr(s.value)
            self.emit(C.STORE_INDEX, (target.name, len(target.args)), s.line)

    def print_(self, s):
        for item in s.items:
            self.expr(item.expr)
            self.emit(C.PRINT_VALUE, None, s.line)
            if item.separator == ",":
                self.emit(C.PRINT_TAB, None, s.line)
        if not s.items or s.items[-1].separator is None:
            self.emit(C.PRINT_NEWLINE, None, s.line)

    def input_(self, s):
        target = s.target
        args = target.args if isinstance(target, nodes.CallOrIndex) else ()
        for index in args:
            self.expr(index)
        self.emit(C.INPUT, (s.prompt, target.name, len(args)), s.line)

    def data_(self, s):
        self.data.values.extend(s.values)

    def read(self, s):
        for target in s.targets:
            args = target.args if isinstance(target, nodes.CallOrIndex) else ()
            for index in args:
                self.expr(index)
            self.emit(C.READ, (target.name, len(args)), s.line)

    def restore(self, s):
        ins = self.emit(C.RESTORE, 0, s.line)
        if s.label is not None:
            self.data.restore_refs.append((ins, s.label))

    def if_(self, s):
        to_end = []
        for cond, body in s.branches:
            self.expr(cond)
            skip = self.emit(C.JUMP_IF_FALSE, None, s.line)
            self.block(body)
            to_end.append(self.emit(C.JUMP, None, s.line))
            skip.arg = self.here()
        if s.else_body:
            self.block(s.else_body)
        for ins in to_end:
            ins.arg = self.here()

    def for_(self, s):
        self.loop_count += 1
        loop_id = self.loop_count
        self.expr(s.start)
        self.emit(C.STORE, s.var, s.line)
        self.expr(s.end)
        self.expr(s.step if s.step is not None else nodes.IntLiteral(1, s.line))
        self.emit(C.FOR_INIT, loop_id, s.line)
        top = self.here()
        check = self.emit(C.FOR_CHECK, None, s.line)
        loop = self.loop_body("FOR", loop_id, s.body)
        self.emit(C.FOR_STEP, (loop_id, s.var, top), s.line)
        check.arg = (loop_id, s.var, self.here())
        self.patch_exits(loop)

    def while_(self, s):
        top = self.here()
        self.expr(s.condition)
        exit_jump = self.emit(C.JUMP_IF_FALSE, None, s.line)
        loop = self.loop_body("WHILE", 0, s.body)
        self.emit(C.JUMP, top, s.line)
        exit_jump.arg = self.here()
        self.patch_exits(loop)

    def loop_body(self, kind, loop_id, body):
        loop = OpenLoop(kind, loop_id, [])
        self.loops.append(loop)
        self.block(body)
        self.loops.pop()
        return loop

    def patch_exits(self, loop):
        for ins in loop.exits:
            ins.arg = self.here()

    def exit_loop(self, s):
        """Jump past the innermost loop of the kind, forgetting the FOR loops being left."""
        for i in range(len(self.loops) - 1, -1, -1):
            if self.loops[i].kind == s.kind:
                break
        else:
            raise BasicSyntaxError("EXIT %s WITHOUT %s" % (s.kind, s.kind), s.line)
        left_fors = [loop for loop in self.loops[i:] if loop.kind == "FOR"]
        if left_fors:
            self.emit(C.FOR_DROP, left_fors[0].loop_id, s.line)     # the outermost one left
        self.loops[i].exits.append(self.emit(C.JUMP, None, s.line))

    def goto(self, s):
        self.emit_to_label(C.JUMP, s.label, s.line)

    def gosub(self, s):
        self.emit_to_label(C.GOSUB, s.label, s.line)

    def return_(self, s):
        if s.value is not None:
            if not self.in_function:
                raise BasicSyntaxError(SYNTAX_ERROR, s.line, "RETURN value outside FUNCTION")
            self.expr(s.value)
            self.emit(C.RETURN_VALUE, None, s.line)
        else:
            self.emit(C.RETURN_ANY if self.in_function else C.RETURN_SUB, None, s.line)

    def end(self, s):
        self.emit(C.END, None, s.line)

    def exit_(self, s):
        self.emit(C.EXIT, None, s.line)

    def dim(self, s):
        for decl in s.arrays:
            for size in decl.sizes:
                self.expr(size)
            self.emit(C.DIM, (decl.name, len(decl.sizes)), s.line)

    def dict_(self, s):
        for name in s.names:
            self.emit(C.DICT, name, s.line)

    def erase(self, s):
        for target in s.targets:
            args = target.args if isinstance(target, nodes.CallOrIndex) else ()
            for key in args:
                self.expr(key)
            self.emit(C.ERASE, (target.name, len(args)), s.line)

    def global_(self, s):
        self.emit(C.GLOBAL, s.names, s.line)

    def command(self, s):
        for arg in s.args:
            self.expr(arg)
        self.emit(C.COMMAND, (s.name, len(s.args)), s.line)

    def call_statement(self, s):
        for arg in s.args:
            self.expr(arg)
        self.emit(C.CALL, (s.name, len(s.args)), s.line)
        self.emit(C.POP, None, s.line)

    STATEMENTS = {
        nodes.Label: label,
        nodes.Assign: assign,
        nodes.Print: print_,
        nodes.Input: input_,
        nodes.If: if_,
        nodes.For: for_,
        nodes.While: while_,
        nodes.Goto: goto,
        nodes.Gosub: gosub,
        nodes.Return: return_,
        nodes.End: end,
        nodes.Exit: exit_,
        nodes.ExitLoop: exit_loop,
        nodes.Dim: dim,
        nodes.Global: global_,
        nodes.DictDecl: dict_,
        nodes.Erase: erase,
        nodes.Command: command,
        nodes.CallStatement: call_statement,
        nodes.Data: data_,
        nodes.Read: read,
        nodes.Restore: restore,
    }

    # --- expressions ---------------------------------------------------------
    def expr(self, e):
        if isinstance(e, (nodes.IntLiteral, nodes.StringLiteral)):
            self.emit(C.PUSH, e.value, e.line)
        elif isinstance(e, nodes.Name):
            self.emit(C.LOAD, e.name, e.line)
        elif isinstance(e, nodes.CallOrIndex):
            for arg in e.args:
                self.expr(arg)
            self.emit(C.LOAD_INDEX, (e.name, len(e.args)), e.line)
        elif isinstance(e, nodes.Unary):
            if e.op == "-" and isinstance(e.operand, nodes.IntLiteral):
                self.emit(C.PUSH, -e.operand.value, e.line)
            else:
                self.expr(e.operand)
                self.emit(C.UNARY, e.op, e.line)
        elif e.op in ("AND", "OR"):
            self.expr(e.left)
            jump = self.emit(C.AND_JUMP if e.op == "AND" else C.OR_JUMP, None, e.line)
            self.expr(e.right)
            self.emit(C.TRUTH, None, e.line)
            jump.arg = self.here()
        else:
            self.expr(e.left)
            self.expr(e.right)
            self.emit(C.BINARY, e.op, e.line)
