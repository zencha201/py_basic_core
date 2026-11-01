"""What the BASIC core needs from its surroundings (DESIGN.md 8).

Input is not part of the host: the runtime reports WAITING_INPUT and the
front end hands the typed line to Runtime.provide_input().
"""

import unicodedata
from typing import Protocol


class Host(Protocol):
    def write(self, text: str) -> None:
        """Show text at the cursor. "\\n" starts a new line."""

    def column(self) -> int:
        """Cursor column in half-width cells (used by PRINT's ',')."""


def cell_width(ch):
    """1 for half-width characters, 2 for full-width ones."""
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


class BufferHost:
    """Collects the output in a string (tests, console front ends)."""

    def __init__(self):
        self.output = ""

    def write(self, text):
        self.output += text

    def column(self):
        last = self.output.rsplit("\n", 1)[-1]
        return sum(cell_width(ch) for ch in last)
