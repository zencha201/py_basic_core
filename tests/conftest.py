"""Load the core package as ``basic_core``, whatever its folder is called.

The core is used as a sub-folder of front ends (for example ``basic/core``)
and also on its own, so the tests do not rely on the folder name.
"""

import importlib.util
import os
import sys

CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = "basic_core"

if PACKAGE not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        PACKAGE, os.path.join(CORE_DIR, "__init__.py"), submodule_search_locations=[CORE_DIR])
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[PACKAGE] = _module
    _spec.loader.exec_module(_module)
