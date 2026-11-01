"""Run BASIC source with the core only (no Pyxel)."""

from basic_core import BufferHost, Runtime, RunState, install_standard


def make_runtime():
    host = BufferHost()
    rt = Runtime(host)
    install_standard(rt)
    return rt, host


def run(source, inputs=()):
    """Output of ``source``; ``inputs`` answers INPUT statements in order."""
    rt, host = make_runtime()
    rt.load(source)
    pending = list(inputs)
    for _ in range(10000):
        state = rt.run(100000)
        if state == RunState.WAITING_INPUT:
            host.write(pending[0] + "\n")
            rt.provide_input(pending.pop(0))
        elif state != RunState.RUNNING:
            break
    if rt.state == RunState.ERROR:
        raise rt.error
    return host.output


def error_of(source):
    rt, _ = make_runtime()
    try:
        rt.load(source)
    except Exception as e:      # syntax error
        return e
    while rt.run(100000) == RunState.RUNNING:
        pass
    return rt.error
