"""One line of text being typed (INPUT and direct mode), with history."""


class LineEditor:
    def __init__(self):
        self.text = ""
        self.cursor = 0
        self.history = []
        self._history_pos = 0

    def clear(self):
        self.text = ""
        self.cursor = 0
        self._history_pos = len(self.history)

    def insert(self, s):
        self.text = self.text[:self.cursor] + s + self.text[self.cursor:]
        self.cursor += len(s)

    def backspace(self):
        if self.cursor > 0:
            self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
            self.cursor -= 1

    def delete(self):
        self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]

    def left(self):
        self.cursor = max(0, self.cursor - 1)

    def right(self):
        self.cursor = min(len(self.text), self.cursor + 1)

    def home(self):
        self.cursor = 0

    def end(self):
        self.cursor = len(self.text)

    def submit(self, remember=False):
        """The finished line; the editor is emptied."""
        line = self.text
        if remember and line.strip() and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self.clear()
        return line

    def history_prev(self):
        if self._history_pos > 0:
            self._history_pos -= 1
            self._show_history()

    def history_next(self):
        if self._history_pos < len(self.history):
            self._history_pos += 1
            self._show_history()

    def _show_history(self):
        pos = self._history_pos
        self.text = self.history[pos] if pos < len(self.history) else ""
        self.cursor = len(self.text)
