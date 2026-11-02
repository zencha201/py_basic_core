"""BASIC language core (DESIGN.md 1).

Pure Python with no outside libraries. Import it as ``py_basic_core`` (put
the repository folder on ``sys.path``). All imports inside the package are
relative.
"""

from .errors import BasicError, BasicRuntimeError, BasicSyntaxError
from .function import CallContext, Suspend, WaitFrames, WaitUntil
from .host import BufferHost, Host
from .repl import ReplSession
from .runtime import Runtime, RunState
from .stdlib import install_http, install_standard

__all__ = [
    "BasicError", "BasicRuntimeError", "BasicSyntaxError",
    "CallContext", "Suspend", "WaitFrames", "WaitUntil",
    "BufferHost", "Host", "ReplSession", "Runtime", "RunState",
    "install_standard", "install_http",
]
