"""Variables, arrays and scopes (BASIC.md 4.9 / 5.3, DESIGN.md 7)."""

from .errors import (ILLEGAL_FUNCTION_CALL, SUBSCRIPT_OUT_OF_RANGE, TYPE_MISMATCH,
                     BasicRuntimeError)
from .values import default_for, expect_int, is_int

MAX_ARRAY_ELEMENTS = 1_000_000


class BasicArray:
    """A 1- or 2-dimensional array. DIM A(10) holds A(0) to A(10)."""

    def __init__(self, name, sizes):
        lengths = []
        for size in sizes:
            size = expect_int(size)
            if size < 0:
                raise BasicRuntimeError(SUBSCRIPT_OUT_OF_RANGE)
            lengths.append(size + 1)
        total = 1
        for n in lengths:
            total *= n
        if total > MAX_ARRAY_ELEMENTS:
            raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail="array too large")
        self.name = name
        self.lengths = tuple(lengths)
        self.data = [default_for(name)] * total

    def _offset(self, indices):
        if len(indices) != len(self.lengths):
            raise BasicRuntimeError(SUBSCRIPT_OUT_OF_RANGE)
        offset = 0
        for index, length in zip(indices, self.lengths):
            index = expect_int(index)
            if not 0 <= index < length:
                raise BasicRuntimeError(SUBSCRIPT_OUT_OF_RANGE)
            offset = offset * length + index
        return offset

    def get(self, indices):
        return self.data[self._offset(indices)]

    def set(self, indices, value):
        self.data[self._offset(indices)] = value


class BasicDict:
    """An associative array made with DICT (BASIC.md 4.14).

    Keys are strings; an integer key is the same as its decimal string
    (HP(1) and HP("1") are one entry). Entries keep the order they were added in.
    """

    def __init__(self, name):
        self.name = name
        self.data = {}
        self._keys = None           # list of keys for KEY$, rebuilt after a change

    @staticmethod
    def key_of(indices):
        if len(indices) != 1:
            raise BasicRuntimeError(SUBSCRIPT_OUT_OF_RANGE, detail="DICT takes one key")
        key = indices[0]
        if is_int(key):
            return str(key)
        if isinstance(key, str):
            return key
        raise BasicRuntimeError(TYPE_MISMATCH)

    def get(self, indices):
        return self.data.get(self.key_of(indices), default_for(self.name))

    def set(self, indices, value):
        key = self.key_of(indices)
        if key not in self.data:
            self._keys = None
        self.data[key] = value

    def has(self, key):
        return self.key_of([key]) in self.data

    def delete(self, indices):
        if self.data.pop(self.key_of(indices), None) is not None:
            self._keys = None

    def clear(self):
        self.data.clear()
        self._keys = None

    def count(self):
        return len(self.data)

    def key_at(self, i):
        """The i-th key (from 0) in the order of addition."""
        if self._keys is None:
            self._keys = list(self.data)
        if not 0 <= i < len(self._keys):
            raise BasicRuntimeError(SUBSCRIPT_OUT_OF_RANGE)
        return self._keys[i]


class Scope:
    """Plain variables, and arrays and DICTs, of the global program or of one function call."""

    def __init__(self):
        self.values = {}
        self.arrays = {}            # name -> BasicArray or BasicDict
