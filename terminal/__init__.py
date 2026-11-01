"""Text terminal model shared by front ends (no Pyxel, DESIGN.md 11)."""

from .buffer import TerminalBuffer
from .line_editor import LineEditor

__all__ = ["TerminalBuffer", "LineEditor"]
