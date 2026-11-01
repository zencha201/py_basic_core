from basic_core.terminal import LineEditor, TerminalBuffer


def test_wrap_and_scroll():
    t = TerminalBuffer(4, 2)
    t.write("ABCDE")
    assert t.text() == "ABCD\nE" and (t.row, t.col) == (1, 1)
    t.write("\nX")
    assert t.text() == "E\nX"


def test_full_width_cells():
    t = TerminalBuffer(5, 3)
    t.write("Aあい")
    assert t.row_text(0) == "Aあい" and t.col == 5
    t.write("う")
    assert t.text() == "Aあい\nう"
    t2 = TerminalBuffer(4, 2)
    t2.write("ABCあ")              # no room for a wide character in the last cell
    assert t2.text() == "ABC\nあ"


def test_layout_and_make_room():
    t = TerminalBuffer(4, 2)
    t.write("? ")
    places, end = t.layout("ABCD")
    assert places == [(0, 2), (0, 3), (1, 0), (1, 1)] and end == (1, 2)
    t.make_room("ABCDEFG")
    assert t.row == 0 and t.row_text(0) == "    "


def test_line_editor():
    e = LineEditor()
    e.insert("AC")
    e.left()
    e.insert("B")
    assert (e.text, e.cursor) == ("ABC", 2)
    e.backspace()
    e.home()
    e.delete()
    assert e.text == "C"
    assert e.submit(remember=True) == "C" and e.text == ""
    e.insert("X")
    e.submit(remember=True)
    e.history_prev()
    assert e.text == "X"
    e.history_prev()
    assert e.text == "C"
    e.history_next()
    e.history_next()
    assert e.text == ""
