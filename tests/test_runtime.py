"""Runtime API: extensions, step-wise running, stop, direct mode (DESIGN.md)."""

import os
import re
import sys

from helpers import make_runtime, run

from py_basic_core import ReplSession, RunState, WaitFrames

CORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "py_basic_core")


def test_register_function_and_command():
    rt, host = make_runtime()
    calls = []
    rt.register_function("TWICE", lambda ctx, args: ctx.expect_int(args[0]) * 2, 1, 1)
    rt.register_command("BEEP", lambda ctx, args: calls.append(list(args)), 0, 2)
    rt.load("BEEP\nBEEP 1,\"A\"\nPRINT TWICE(21)")
    assert rt.run() == RunState.FINISHED
    assert host.output == "42\n" and calls == [[], [1, "A"]]


def test_extension_errors_are_basic_errors():
    rt, _ = make_runtime()
    rt.register_function("BAD", lambda ctx, args: 1 / 0)
    rt.register_command("ONE", lambda ctx, args: None, 1, 1)
    rt.load("PRINT BAD()")
    assert rt.run() == RunState.ERROR and rt.error.name == "ILLEGAL FUNCTION CALL"
    rt.load("ONE")
    assert rt.run() == RunState.ERROR and rt.error.name == "ARGUMENT COUNT MISMATCH"


def test_run_is_resumable_and_stoppable():
    rt, host = make_runtime()
    rt.load("*L\nA=A+1\nGOTO L")
    assert rt.run(1000) == RunState.RUNNING
    assert rt.run(1000) == RunState.RUNNING
    rt.stop()
    assert rt.run(1000) == RunState.STOPPED


def test_wait_frames():
    rt, host = make_runtime()
    rt.register_command("WAIT", lambda ctx, args: WaitFrames(args[0]), 1, 1)
    rt.load("PRINT 1\nWAIT 2\nPRINT 2")
    assert rt.run() == RunState.WAITING_FRAMES and host.output == "1\n"
    assert rt.run() == RunState.WAITING_FRAMES
    assert rt.run() == RunState.FINISHED and host.output == "1\n2\n"


def test_input_inside_function_suspends():
    out = run("PRINT ASK()\nFUNCTION ASK()\nINPUT N\nRETURN N*2\nEND FUNCTION", ["21"])
    assert out == "? 21\n42\n"


def test_direct_mode_keeps_variables():
    rt, host = make_runtime()
    repl = ReplSession(rt)
    repl.start()
    for line in ("A=5", "PRINT A*2", "PRINT 1/0", "FOR I=1 TO 3:PRINT I;:NEXT:PRINT", "PRINT (", "EXIT"):
        host.write(line + "\n")
        if repl.submit(line):
            while rt.run() == RunState.RUNNING:
                pass
            repl.finish()
    assert host.output == (
        "READY.\nA=5\nREADY.\nPRINT A*2\n10\nREADY.\nPRINT 1/0\n?DIVISION BY ZERO\nREADY.\n"
        "FOR I=1 TO 3:PRINT I;:NEXT:PRINT\n123\nREADY.\nPRINT (\n?SYNTAX ERROR (expression expected)\n"
        "READY.\nEXIT\n")
    assert rt.state == RunState.EXITED


def test_direct_mode_rejects_function_and_program_rejects_exit():
    rt, host = make_runtime()
    repl = ReplSession(rt)
    assert not repl.submit("FUNCTION F()")
    assert "NOT ALLOWED IN DIRECT MODE" in host.output
    try:
        rt.load("EXIT")
        raise AssertionError("EXIT accepted in a program")
    except Exception as e:
        assert e.name == "SYNTAX ERROR"


def test_core_uses_only_the_standard_library():
    """No Pyxel, no outside libraries: every import is relative or from the standard library."""
    for dirpath, dirnames, files in os.walk(CORE_DIR):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            with open(os.path.join(dirpath, f), encoding="utf-8") as fp:
                for line in fp:
                    m = re.match(r"\s*(?:from|import)\s+([\w.]+)", line)
                    if m and not m.group(1).startswith("."):
                        top = m.group(1).split(".")[0]
                        assert top in sys.stdlib_module_names, "%s: %s" % (f, line.strip())
