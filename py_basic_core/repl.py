"""Direct mode (REPL, BASIC.md 8.2) independent of any screen.

The front end shows the prompt, collects a typed line, calls submit() and
then runs the runtime as usual; when the line has finished it calls
finish() to report errors and print READY. again.
"""

from .errors import BasicSyntaxError
from .runtime import RunState

READY = "READY."


class ReplSession:
    def __init__(self, runtime):
        self.runtime = runtime

    def start(self):
        self.runtime.host.write(READY + "\n")

    def submit(self, line):
        """Load a typed line. Returns False when there is nothing to run."""
        if line.strip() == "":
            return False
        try:
            self.runtime.load_direct(line)
        except BasicSyntaxError as e:
            self.runtime.host.write(e.message(with_line=False) + "\n" + READY + "\n")
            return False
        return True

    def finish(self):
        """Call when the runtime reached a final state after submit()."""
        rt = self.runtime
        if rt.state == RunState.ERROR:
            rt.host.write(rt.error.message(with_line=False) + "\n")
        if rt.state != RunState.EXITED:
            rt.host.write(READY + "\n")
