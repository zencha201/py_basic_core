"""Standard commands and functions, added through the same API as any extension."""

from . import standard_commands, standard_functions


def install_standard(runtime):
    standard_commands.install(runtime)
    standard_functions.install(runtime)
