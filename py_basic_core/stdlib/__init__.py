"""Standard commands and functions, added through the same API as any extension.

HTTP (http.install_http) is not standard: an application adds it when its BASIC
programs may use the network.
"""

from . import standard_commands, standard_functions
from .http import install_http  # noqa: F401


def install_standard(runtime):
    standard_commands.install(runtime)
    standard_functions.install(runtime)
