"""Character cells of a text screen: cursor, wrapping and scrolling.

A full-width character takes two cells; the second one holds WIDE_TAIL.
"""

import unicodedata

BLANK = " "
WIDE_TAIL = ""


def default_cell_width(ch):
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


class TerminalBuffer:
    def __init__(self, cols, rows, cell_width=default_cell_width):
        self.cols = max(2, cols)
        self.rows = max(1, rows)
        self.cell_width = cell_width
        self.clear()

    def clear(self):
        self.cells = [self._blank_row() for _ in range(self.rows)]
        self.row = 0
        self.col = 0

    def _blank_row(self):
        return [BLANK] * self.cols

    # --- output ----------------------------------------------------------------
    def write(self, text):
        for ch in text:
            if ch == "\n":
                self.newline()
            elif ch == "\t":
                self.write(BLANK * (8 - self.col % 8))
            elif ch >= " ":
                self.put(ch)

    def put(self, ch):
        w = self.cell_width(ch)
        if self.col + w > self.cols:
            self.newline()
        line = self.cells[self.row]
        line[self.col] = ch
        if w == 2:
            line[self.col + 1] = WIDE_TAIL
        self.col += w      # a full row wraps when the next character arrives

    def newline(self):
        self.col = 0
        self.row += 1
        if self.row >= self.rows:
            self.scroll(1)

    def scroll(self, n):
        n = min(n, self.rows)
        del self.cells[:n]
        self.cells.extend(self._blank_row() for _ in range(n))
        self.row = max(0, self.row - n)

    # --- reading ---------------------------------------------------------------
    def row_text(self, r):
        return "".join(self.cells[r])

    def text(self):
        """All rows, trailing blanks removed (tests)."""
        lines = [self.row_text(r).rstrip() for r in range(self.rows)]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    # --- text being typed (drawn over the buffer, not stored) -------------------
    def layout(self, text):
        """(row, col) of each character of ``text`` written from the cursor,
        and the position after it. Rows may go past the bottom."""
        row, col = self.row, self.col
        places = []
        for ch in text:
            w = self.cell_width(ch)
            if col + w > self.cols:
                row, col = row + 1, 0
            places.append((row, col))
            col += w
        if col >= self.cols:
            row, col = row + 1, 0
        return places, (row, col)

    def make_room(self, text):
        """Scroll so that ``text`` typed at the cursor (and the caret after it) fits."""
        _, (end_row, _) = self.layout(text)
        overflow = end_row - (self.rows - 1)
        if overflow > 0:
            self.scroll(overflow)
