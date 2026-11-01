"""BASIC language core (DESIGN.md 1).

Pure Python with no outside libraries. All imports inside the package are
relative, so it works under any folder name (for example as ``basic.core``
inside a front end, or on its own).
"""

from .errors import BasicError, BasicRuntimeError, BasicSyntaxError
from .function import CallContext, Suspend, WaitFrames
from .host import BufferHost, Host
from .repl import ReplSession
from .runtime import Runtime, RunState
from .stdlib import install_standard

__all__ = [
    "BasicError", "BasicRuntimeError", "BasicSyntaxError",
    "CallContext", "Suspend", "WaitFrames",
    "BufferHost", "Host", "ReplSession", "Runtime", "RunState",
    "install_standard",
]
