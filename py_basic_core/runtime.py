"""Runtime: the stack machine that runs compiled BASIC code (DESIGN.md 6).

run() executes a limited number of instructions and returns, so a front end
can call it once per frame. INPUT and commands that wait (WAIT) pause the
program; the front end resumes it with provide_input() or by calling run()
on the following frames.
"""

from dataclasses import dataclass, field
from typing import Optional

from . import instructions as C
from .compiler import compile_program
from .errors import (DIVISION_BY_ZERO, OUT_OF_DATA, ILLEGAL_FUNCTION_CALL, NAME_CONFLICT,
                     NEXT_WITHOUT_FOR, REDIM, RETURN_WITHOUT_GOSUB, STACK_OVERFLOW, STEP_IS_ZERO,
                     TYPE_MISMATCH, UNDEFINED_ARRAY, UNDEFINED_FUNCTION, BasicError,
                     BasicRuntimeError)
from .function import (CallContext, Suspend, WaitFrames, WaitUntil, bind_arguments,
                       check_arg_count)
from .lexer import tokenize
from .parser import parse
from .registry import Registry
from .values import (check_for_name, check_value, default_for, expect_int, is_string_name,
                     parse_int, to_text)
from .variable import BasicArray, BasicDict, Scope

DEFAULT_MAX_CALL_DEPTH = 1000
PRINT_ZONE = 8          # PRINT "," moves to the next multiple of this column

_MISSING = object()


class RunState:
    IDLE = "IDLE"                   # nothing loaded
    RUNNING = "RUNNING"             # more to run: call run() again
    WAITING_INPUT = "WAITING_INPUT"  # INPUT: call provide_input()
    WAITING_FRAMES = "WAITING_FRAMES"  # WAIT: each run() call counts one frame
    FINISHED = "FINISHED"           # END or end of source
    EXITED = "EXITED"               # EXIT (direct mode)
    STOPPED = "STOPPED"             # stop() was called
    ERROR = "ERROR"                 # see Runtime.error

    DONE = frozenset((FINISHED, EXITED, STOPPED, ERROR))


@dataclass
class Loop:
    loop_id: int
    end: int
    step: int


@dataclass
class Frame:
    """The main program or one call of a user function."""
    code: C.CodeUnit
    scope: Scope
    function: object = None             # UserFunction, None for the main program
    params: dict = field(default_factory=dict)
    pc: int = 0
    stack_base: int = 0
    gosub_stack: list = field(default_factory=list)
    loops: list = field(default_factory=list)
    # ON ERROR (BASIC.md 4.16): where to go, by GOTO or GOSUB, when an error happens
    # in this frame or in a function it called.
    error_target: Optional[int] = None
    error_gosub: bool = False
    in_error_gosub: bool = False       # handling an error with ON ERROR GOSUB until its RETURN
    error_gosub_depth: int = 0         # len(gosub_stack) inside that subroutine
    event: bool = False                # a function called by call_event()


class Runtime:
    def __init__(self, host, max_call_depth=DEFAULT_MAX_CALL_DEPTH):
        self.host = host
        self.registry = Registry()
        self.max_call_depth = max_call_depth
        self.globals = Scope()
        self.functions = {}
        self.state = RunState.IDLE
        self.error = None
        self.stack = []
        self.frames = []
        self._line = 0
        self._wait_frames = 0
        self._wait_until = None     # WaitUntil.ready while waiting for a condition
        self._event = None          # state saved by call_event() until the event function returns
        self.ended_by_end = False   # FINISHED by an END statement (not by the end of the source)
        self._pending_input = None
        self.last_error = None      # the error caught by ON ERROR (ERR$ / ERL)
        self.data = ()              # DATA values of the loaded program
        self.data_pos = 0           # next value READ takes
        self._ops = {
            C.PUSH: self.op_push, C.POP: self.op_pop,
            C.LOAD: self.op_load, C.STORE: self.op_store,
            C.LOAD_INDEX: self.op_load_index, C.STORE_INDEX: self.op_store_index,
            C.DIM: self.op_dim, C.GLOBAL: self.op_global,
            C.DICT: self.op_dict, C.ERASE: self.op_erase,
            C.UNARY: self.op_unary, C.BINARY: self.op_binary, C.TRUTH: self.op_truth,
            C.AND_JUMP: self.op_and_jump, C.OR_JUMP: self.op_or_jump,
            C.JUMP: self.op_jump, C.JUMP_IF_FALSE: self.op_jump_if_false,
            C.FOR_INIT: self.op_for_init, C.FOR_CHECK: self.op_for_check, C.FOR_STEP: self.op_for_step,
            C.FOR_DROP: self.op_for_drop,
            C.GOSUB: self.op_gosub, C.RETURN_SUB: self.op_return_sub,
            C.RETURN_ANY: self.op_return_any, C.RETURN_VALUE: self.op_return_value,
            C.CALL: self.op_call, C.END: self.op_end, C.EXIT: self.op_exit,
            C.PRINT_VALUE: self.op_print_value, C.PRINT_TAB: self.op_print_tab,
            C.PRINT_NEWLINE: self.op_print_newline,
            C.INPUT: self.op_input, C.COMMAND: self.op_command,
            C.READ: self.op_read, C.RESTORE: self.op_restore,
            C.JUMP_IF_TRUE: self.op_jump_if_true, C.CASE_MATCH: self.op_case_match,
            C.ON_ERROR_GOTO: self.op_on_error_goto, C.ON_ERROR_GOSUB: self.op_on_error_gosub,
            C.ON_ERROR_OFF: self.op_on_error_off,
        }

    # --- extension API (DESIGN.md 8) -------------------------------------------
    def register_function(self, name, fn, min_args=0, max_args=None):
        self.registry.register_function(name, fn, min_args, max_args)

    def register_command(self, name, fn, min_args=0, max_args=None):
        self.registry.register_command(name, fn, min_args, max_args)

    # --- loading -------------------------------------------------------------
    def load(self, source):
        """Parse and compile a whole program and get ready to run it.

        Raises BasicSyntaxError. Variables start empty.
        """
        compiled = self._compile(source, direct_mode=False)
        self.globals = Scope()
        self.functions = compiled.functions
        self._start(compiled)

    def load_direct(self, line):
        """Get ready to run one line typed in direct mode, keeping the variables."""
        compiled = self._compile(line, direct_mode=True)
        self._start(compiled)

    def _compile(self, source, direct_mode):
        tokens = tokenize(source)
        program = parse(tokens, self.registry.command_names(), direct_mode)
        return compile_program(program)

    def _start(self, compiled):
        self.stack = []
        self.frames = [Frame(compiled.main, self.globals)]
        self.data = compiled.data
        self.data_pos = 0
        self.error = None
        self.last_error = None
        self._pending_input = None
        self._wait_frames = 0
        self._wait_until = None
        self._event = None
        self.ended_by_end = False
        self.state = RunState.RUNNING

    def stop(self):
        if self.state not in RunState.DONE:
            self.state = RunState.STOPPED

    # --- running -------------------------------------------------------------
    def run(self, max_steps=10000):
        """Run up to ``max_steps`` instructions and return the state."""
        if self.state == RunState.WAITING_FRAMES:
            if self._wait_until is not None:
                if not self._wait_until():
                    return self.state
                self._wait_until = None
            else:
                self._wait_frames -= 1
                if self._wait_frames > 0:
                    return self.state
            self.state = RunState.RUNNING
        if self.state != RunState.RUNNING:
            return self.state
        ops = self._ops
        for _ in range(max_steps):
            frame = self.frames[-1]
            ins = frame.code.instructions[frame.pc]
            frame.pc += 1
            self._line = ins.line
            try:
                ops[ins.op](ins.arg)
            except BasicError as e:
                self._error(e)
            if self.state != RunState.RUNNING:
                break
        return self.state

    def _error(self, error):
        """Go to the ON ERROR handler, or stop with the error."""
        if error.line is None:
            error.line = self._line
        if not (isinstance(error, BasicRuntimeError) and self._trap(error)):
            self.error = error
            self.state = RunState.ERROR

    def _trap(self, error):
        """Jump to the nearest ON ERROR handler; frames above it are left (BASIC.md 4.16).

        An event function (call_event) is a boundary: handlers below it are not used.
        """
        lowest = 0
        for i in range(len(self.frames) - 1, -1, -1):
            if self.frames[i].event:
                lowest = i
                break
        for i in range(len(self.frames) - 1, lowest - 1, -1):
            frame = self.frames[i]
            if frame.error_target is not None and not frame.in_error_gosub:
                break
        else:
            return False
        del self.frames[i + 1:]
        del self.stack[frame.stack_base:]
        self.last_error = error
        if frame.error_gosub:
            # RETURN goes on after the statement that failed (or the call that led to it).
            frame.gosub_stack.append(frame.code.resume_points[frame.pc - 1])
            frame.in_error_gosub = True
            frame.error_gosub_depth = len(frame.gosub_stack)
        frame.pc = frame.error_target
        return True

    @property
    def line(self):
        """Source line of the instruction run last."""
        return self._line

    def provide_input(self, text):
        """The line typed for a pending INPUT."""
        if self.state != RunState.WAITING_INPUT:
            return
        prompt, name, indices = self._pending_input
        if is_string_name(name):
            value = text
        else:
            value = parse_int(text)
            if value is None:
                self.host.write("?REDO\n")
                self.host.write(prompt)
                return
        self._pending_input = None
        self.state = RunState.RUNNING
        try:
            if indices is None:
                self._store(name, value)
            else:
                self._array_for_write(name).set(indices, value)
        except BasicError as e:
            self._error(e)

    # --- stack helpers ---------------------------------------------------------
    def _pop_n(self, n):
        if n == 0:
            return []
        values = self.stack[-n:]
        del self.stack[-n:]
        return values

    # --- variables (name resolution: BASIC.md 5.5) --------------------------------
    def _load(self, name):
        frame = self.frames[-1]
        value = frame.scope.values.get(name, _MISSING)
        if value is _MISSING:
            if name in frame.params:
                value = frame.params[name]
            elif name in frame.code.global_names:
                value = self.globals.values.get(name, _MISSING)
        if value is _MISSING:
            container = self._find_array(name)
            if isinstance(container, BasicDict):
                return container        # a bare DICT name stands for the DICT itself
            return default_for(name)
        return value

    def _store(self, name, value):
        check_for_name(name, value)
        frame = self.frames[-1]
        if name in frame.params:
            frame.params[name] = value
            return
        scope = self._write_scope(frame, name)
        if name in scope.arrays:
            raise BasicRuntimeError(NAME_CONFLICT, detail=name)
        scope.values[name] = value

    def _write_scope(self, frame, name):
        if frame.function is None or name in frame.code.global_names:
            return self.globals
        return frame.scope

    def _find_array(self, name):
        frame = self.frames[-1]
        array = frame.scope.arrays.get(name)
        if array is None and name in frame.code.global_names:
            array = self.globals.arrays.get(name)
        return array

    def _array_for_write(self, name):
        array = self._find_array(name)
        if array is None:
            raise BasicRuntimeError(UNDEFINED_ARRAY, detail=name)
        return array

    # --- instructions: values and variables --------------------------------------
    def op_push(self, value):
        self.stack.append(value)

    def op_pop(self, _):
        self.stack.pop()

    def op_load(self, name):
        self.stack.append(self._load(name))

    def op_store(self, name):
        self._store(name, self.stack.pop())

    def op_load_index(self, arg):
        name, n = arg
        args = self._pop_n(n)
        array = self._find_array(name)
        if array is not None:
            self.stack.append(array.get(args))
        else:
            self._call(name, args)

    def op_store_index(self, arg):
        name, n = arg
        value = self.stack.pop()
        indices = self._pop_n(n)
        check_for_name(name, value)
        self._array_for_write(name).set(indices, value)

    def op_dim(self, arg):
        name, n = arg
        sizes = self._pop_n(n)
        self._new_container(name, lambda: BasicArray(name, sizes))

    def op_dict(self, name):
        self._new_container(name, lambda: BasicDict(name))

    def _new_container(self, name, create):
        scope = self._write_scope(self.frames[-1], name)
        if name in scope.arrays:
            raise BasicRuntimeError(REDIM, detail=name)
        if name in scope.values:
            raise BasicRuntimeError(NAME_CONFLICT, detail=name)
        scope.arrays[name] = create()

    def op_erase(self, arg):
        name, n = arg
        keys = self._pop_n(n)
        container = self._array_for_write(name)
        if not isinstance(container, BasicDict):
            raise BasicRuntimeError(TYPE_MISMATCH, detail="ERASE needs a DICT")
        if keys:
            container.delete(keys)
        else:
            container.clear()

    def op_global(self, names):
        for name in names:
            if name not in self.globals.values and name not in self.globals.arrays:
                self.globals.values[name] = default_for(name)

    # --- instructions: operators ---------------------------------------------------
    def op_unary(self, op):
        value = expect_int(self.stack.pop())
        if op == "-":
            value = -value
        elif op == "NOT":
            value = 0 if value else 1
        self.stack.append(value)

    def op_binary(self, op):
        right = self.stack.pop()
        left = self.stack.pop()
        self.stack.append(binary(op, left, right))

    def op_truth(self, _):
        self.stack[-1] = 1 if expect_int(self.stack[-1]) else 0

    def op_and_jump(self, target):
        if expect_int(self.stack[-1]):
            self.stack.pop()
        else:
            self.stack[-1] = 0
            self.frames[-1].pc = target

    def op_or_jump(self, target):
        if expect_int(self.stack[-1]):
            self.stack[-1] = 1
            self.frames[-1].pc = target
        else:
            self.stack.pop()

    # --- instructions: control flow ---------------------------------------------------
    def op_jump(self, target):
        self.frames[-1].pc = target

    def op_jump_if_false(self, target):
        if not expect_int(self.stack.pop()):
            self.frames[-1].pc = target

    def _loop_index(self, frame, loop_id):
        for i in range(len(frame.loops) - 1, -1, -1):
            if frame.loops[i].loop_id == loop_id:
                return i
        return -1

    def op_for_init(self, loop_id):
        step = expect_int(self.stack.pop())
        end = expect_int(self.stack.pop())
        if step == 0:
            raise BasicRuntimeError(STEP_IS_ZERO)
        frame = self.frames[-1]
        i = self._loop_index(frame, loop_id)
        if i >= 0:
            del frame.loops[i:]         # the loop was left with GOTO and is started again
        frame.loops.append(Loop(loop_id, end, step))

    def op_for_check(self, arg):
        loop_id, var, exit_target = arg
        frame = self.frames[-1]
        i = self._loop_index(frame, loop_id)
        if i < 0:
            raise BasicRuntimeError(NEXT_WITHOUT_FOR)
        loop = frame.loops[i]
        value = expect_int(self._load(var))
        if (loop.step > 0 and value > loop.end) or (loop.step < 0 and value < loop.end):
            del frame.loops[i:]
            frame.pc = exit_target

    def op_for_step(self, arg):
        loop_id, var, top = arg
        frame = self.frames[-1]
        i = self._loop_index(frame, loop_id)
        if i < 0:
            raise BasicRuntimeError(NEXT_WITHOUT_FOR)
        self._store(var, expect_int(self._load(var)) + frame.loops[i].step)
        frame.pc = top

    def op_for_drop(self, loop_id):
        frame = self.frames[-1]
        i = self._loop_index(frame, loop_id)
        if i >= 0:
            del frame.loops[i:]

    def op_jump_if_true(self, target):
        if expect_int(self.stack.pop()):
            self.frames[-1].pc = target

    def op_case_match(self, kind):
        """One CASE test; the selector stays on the stack (BASIC.md 4.15)."""
        if kind == "TO":
            last = self.stack.pop()
            first = self.stack.pop()
            selector = self.stack[-1]
            hit = binary(">=", selector, first) and binary("<=", selector, last)
        else:
            value = self.stack.pop()
            hit = binary(kind, self.stack[-1], value)
        self.stack.append(1 if hit else 0)

    def op_on_error_goto(self, target):
        self._set_error_handler(target, gosub=False)

    def op_on_error_gosub(self, target):
        self._set_error_handler(target, gosub=True)

    def op_on_error_off(self, _):
        self._set_error_handler(None, gosub=False)

    def _set_error_handler(self, target, gosub):
        frame = self.frames[-1]
        frame.error_target = target
        frame.error_gosub = gosub

    def op_gosub(self, target):
        frame = self.frames[-1]
        frame.gosub_stack.append(frame.pc)
        frame.pc = target

    def op_return_sub(self, _):
        frame = self.frames[-1]
        if not frame.gosub_stack:
            raise BasicRuntimeError(RETURN_WITHOUT_GOSUB)
        self._return_from_gosub(frame)

    def op_return_any(self, _):
        frame = self.frames[-1]
        if frame.gosub_stack:
            self._return_from_gosub(frame)
        else:
            self._return(default_for(frame.function.name))

    def _return_from_gosub(self, frame):
        if frame.in_error_gosub and len(frame.gosub_stack) == frame.error_gosub_depth:
            frame.in_error_gosub = False        # the ON ERROR GOSUB routine is done
        frame.pc = frame.gosub_stack.pop()

    def op_return_value(self, _):
        self._return(self.stack.pop())

    def _return(self, value):
        frame = self.frames.pop()
        check_for_name(frame.function.name, value)
        del self.stack[frame.stack_base:]
        if frame.event:
            # Back to what the program was doing before the event (the value is not used).
            self.state, self._wait_frames, self._wait_until = self._event
            self._event = None
        else:
            self.stack.append(value)

    # --- events (called by front ends, e.g. a GUI) ------------------------------------
    def has_function(self, name):
        return name.upper() in self.functions

    @property
    def in_event(self):
        return self._event is not None

    def call_event(self, name):
        """Call the user function ``name`` (no arguments) as an event, e.g. a button click.

        Possible while the program is running between run() calls, waiting (WAIT)
        or finished at the end of the source. The function runs with the following
        run() calls; when it returns, the program goes back to what it was doing.
        Returns False when the call is not possible now (another event is running,
        the program has ended with END or an error, or there is no such function).
        """
        function = self.functions.get(name.upper())
        possible = (self.state in (RunState.RUNNING, RunState.WAITING_FRAMES)
                    or (self.state == RunState.FINISHED and not self.ended_by_end))
        if function is None or function.min_args or self._event is not None or not possible:
            return False
        if len(self.frames) > self.max_call_depth:
            return False
        self._event = (self.state, self._wait_frames, self._wait_until)
        self._wait_until = None
        self.frames.append(Frame(function.code, Scope(), function, {}, stack_base=len(self.stack),
                                 event=True))
        self.state = RunState.RUNNING
        return True

    def op_call(self, arg):
        name, n = arg
        self._call(name, self._pop_n(n))

    def _call(self, name, args):
        """Call a user function (pushes a frame) or a built-in one (pushes the result)."""
        function = self.functions.get(name)
        if function is not None:
            if len(self.frames) > self.max_call_depth:
                raise BasicRuntimeError(STACK_OVERFLOW)
            params = bind_arguments(function, args)
            self.frames.append(Frame(function.code, Scope(), function, params,
                                     stack_base=len(self.stack)))
            return
        builtin = self.registry.functions.get(name)
        if builtin is None:
            raise BasicRuntimeError(UNDEFINED_FUNCTION, detail=name)
        check_arg_count(builtin, args)
        result = self._call_python(builtin, args)
        if isinstance(result, bool) or not isinstance(result, (int, str)):
            raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail=name)
        self.stack.append(check_for_name(name, result))

    def _call_python(self, callable_, args):
        try:
            return callable_.fn(CallContext(self, callable_.name, self._line), args)
        except BasicError:
            raise
        except Exception as e:      # a bug or bad input in an extension: report, do not crash
            raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail="%s: %s" % (callable_.name, e))

    def op_end(self, explicit):
        self.ended_by_end = bool(explicit)
        self._event = None
        self.state = RunState.FINISHED

    def op_exit(self, _):
        self.state = RunState.EXITED

    # --- instructions: input / output ---------------------------------------------------
    def op_print_value(self, _):
        self.host.write(to_text(check_value(self.stack.pop())))

    def op_print_tab(self, _):
        self.host.write(" " * (PRINT_ZONE - self.host.column() % PRINT_ZONE))

    def op_print_newline(self, _):
        self.host.write("\n")

    def op_input(self, arg):
        prompt, name, n = arg
        indices = self._pop_n(n) if n else None
        if indices is not None:
            self._array_for_write(name)     # report a missing array before asking
        text = (prompt or "") + "? "
        self.host.write(text)
        self._pending_input = (text, name, indices)
        self.state = RunState.WAITING_INPUT

    def op_read(self, arg):
        name, n = arg
        indices = self._pop_n(n) if n else None
        if self.data_pos >= len(self.data):
            raise BasicRuntimeError(OUT_OF_DATA)
        value = self.data[self.data_pos]
        self.data_pos += 1
        if indices is None:
            self._store(name, value)
        else:
            check_for_name(name, value)
            self._array_for_write(name).set(indices, value)

    def op_restore(self, position):
        self.data_pos = position

    def op_command(self, arg):
        name, n = arg
        args = self._pop_n(n)
        spec = self.registry.commands[name]
        check_arg_count(spec, args)
        result = self._call_python(spec, args)
        if isinstance(result, WaitFrames):
            if result.frames > 0:
                self._wait_frames = result.frames
                self.state = RunState.WAITING_FRAMES
        elif isinstance(result, WaitUntil):
            self._wait_until = result.ready
            self.state = RunState.WAITING_FRAMES
        elif isinstance(result, Suspend):
            raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail=name)


def binary(op, left, right):
    """Result of a binary operator (BASIC.md 3.2 - 3.4). AND / OR are compiled as jumps."""
    if op == "+":
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        return expect_int(left) + expect_int(right)
    if op in ("=", "<>", "<", "<=", ">", ">="):
        check_value(left)
        check_value(right)
        if isinstance(left, str) != isinstance(right, str):
            raise BasicRuntimeError(TYPE_MISMATCH)
        return 1 if COMPARE[op](left, right) else 0
    a = expect_int(left)
    b = expect_int(right)
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if b == 0:
        raise BasicRuntimeError(DIVISION_BY_ZERO)
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q                      # truncate toward zero
    return q if op == "/" else a - b * q


COMPARE = {
    "=": lambda a, b: a == b,
    "<>": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}
