"""Standard commands and functions, added through the same API as any extension.

HTTP (http.install_http) and DWRITE / DREAD (dictfile.install_dict_files) are
not standard: an application adds them when its BASIC programs may use the
network or files.
"""

from . import standard_commands, standard_functions
from .dictfile import install_dict_files  # noqa: F401
from .http import install_http  # noqa: F401


def install_standard(runtime):
    standard_commands.install(runtime)
    standard_functions.install(runtime)
