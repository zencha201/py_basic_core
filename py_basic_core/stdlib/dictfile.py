"""Saving a DICT to a file and reading it back: DWRITE / DREAD (BASIC.md 6.2).

    DICT SAVE$
    SAVE$("name") = "TARO"
    DWRITE "save.json", SAVE$
    DREAD "save.json", SAVE$

The file is JSON (UTF-8): DWRITE writes the DICT as one flat object in the
order of its keys, numbers for an INT DICT and strings for a STRING DICT, so
DREAD gives back the same DICT. DREAD also reads other JSON files (objects and
arrays), flattened like the reply of HTTP.

Not part of install_standard(): an application that lets BASIC programs use
files calls install_dict_files(runtime, base_dir).
"""

import json
import os

from ..errors import FILE_NOT_FOUND, ILLEGAL_FUNCTION_CALL
from .dictjson import flat_value, flatten, int_value, parse_json

MAX_BYTES = 16 * 1024 * 1024    # largest file read


def install_dict_files(runtime, base_dir=os.getcwd):
    """Register DWRITE / DREAD. ``base_dir()`` gives the folder of relative file names."""

    def path_of(ctx, value):
        name = ctx.expect_str(value).strip()
        if not name:
            raise ctx.error(ILLEGAL_FUNCTION_CALL, "no file name")
        return name, os.path.join(base_dir(), name)

    def is_string_dict(d):
        return d.name.endswith("$")

    def dwrite(ctx, args):
        """DWRITE file$, dict"""
        name, path = path_of(ctx, args[0])
        d = ctx.expect_dict(args[1])
        text = json.dumps(dict(d.data), ensure_ascii=False, indent=2) + "\n"
        temp = path + ".tmp"
        try:
            with open(temp, "w", encoding="utf-8", newline="\n") as fp:
                fp.write(text)
            os.replace(temp, path)      # a crash while writing never leaves half a file
        except OSError as e:
            try:
                os.remove(temp)
            except OSError:
                pass
            raise ctx.error(ILLEGAL_FUNCTION_CALL, "cannot write %s: %s" % (name, e.strerror or e))

    def dread(ctx, args):
        """DREAD file$, dict: the DICT is emptied, then filled from the file."""
        name, path = path_of(ctx, args[0])
        d = ctx.expect_dict(args[1])
        if not os.path.isfile(path):
            raise ctx.error(FILE_NOT_FOUND, name)
        try:
            if os.path.getsize(path) > MAX_BYTES:
                raise ctx.error(ILLEGAL_FUNCTION_CALL, "%s is larger than %d bytes" % (name, MAX_BYTES))
            with open(path, encoding="utf-8-sig") as fp:
                text = fp.read()
        except (OSError, UnicodeDecodeError) as e:
            raise ctx.error(ILLEGAL_FUNCTION_CALL, "cannot read %s: %s" % (name, e))
        data = parse_json(text)
        if data is None:
            raise ctx.error(ILLEGAL_FUNCTION_CALL, "not a JSON object or array: " + name)
        items = flatten(data, convert=flat_value if is_string_dict(d) else int_value)
        d.clear()                       # only after the whole file was read and converted
        for key, value in items:
            d.set([key], value)

    runtime.register_command("DWRITE", dwrite, 2, 2)
    runtime.register_command("DREAD", dread, 2, 2)
