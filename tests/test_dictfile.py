"""DWRITE / DREAD (BASIC.md 6.2)."""

import json

from py_basic_core import BufferHost, Runtime, RunState, install_dict_files, install_standard


def run(source, folder):
    host = BufferHost()
    rt = Runtime(host)
    install_standard(rt)
    install_dict_files(rt, lambda: str(folder))
    rt.load(source)
    rt.run(100000)
    return rt, host.output


def test_write_and_read_back(tmp_path):
    rt, out = run('''
DICT S$, N
S$("name") = "タロウ"
S$("memo") = "a""b" + CHR$(10) + "c"
S$("pos.x") = "3"
N("hp") = 30
N("gold") = -5
DWRITE "save.json", S$
DWRITE "nums.json", N
DICT T$, M
T$("OLD") = "X"
DREAD "save.json", T$
DREAD "nums.json", M
FOR I = 0 TO COUNT(T$) - 1
    PRINT KEY$(T$, I); "="; T$(KEY$(T$, I))
NEXT
PRINT M("hp") + M("gold"); COUNT(M)
''', tmp_path)
    assert rt.state == RunState.FINISHED, rt.error
    assert out.split("\n")[:5] == ["name=タロウ", 'memo=a"b', "c", "pos.x=3", "252"]
    assert json.loads((tmp_path / "save.json").read_text(encoding="utf-8")) == {
        "name": "タロウ", "memo": 'a"b\nc', "pos.x": "3"}
    assert json.loads((tmp_path / "nums.json").read_text(encoding="utf-8")) == {"hp": 30, "gold": -5}
    assert not list(tmp_path.glob("*.tmp"))


def test_read_other_json_files(tmp_path):
    (tmp_path / "data.json").write_text(
        '{"user": {"name": "TARO", "ok": true}, "items": [3, 4.5, null], "level": "7"}',
        encoding="utf-8")
    rt, out = run('''
DICT S$, N
DREAD "data.json", S$
PRINT S$("user.name"); " "; S$("user.ok"); " "; S$("items.1"); " "; S$("items.#")
DREAD "data.json", N
''', tmp_path)
    assert out.startswith("TARO 1 4.5 3")
    assert rt.state == RunState.ERROR and "TYPE MISMATCH" in rt.error.message()   # "TARO" in an INT DICT
    (tmp_path / "n.json").write_text('{"a": 1, "b": "2", "c": [true, 2.9], "d": null}', encoding="utf-8")
    rt, out = run('DICT N\nDREAD "n.json", N\nPRINT N("a");N("b");N("c.0");N("c.1");N("c.#");N("d")',
                  tmp_path)
    assert out.startswith("121220")


def test_errors(tmp_path):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    for source, message in [
        ('DICT D$\nDREAD "none.json", D$', "FILE NOT FOUND (none.json)"),
        ('DICT D$\nDREAD "bad.json", D$', "not a JSON object or array"),
        ('DICT D$\nDWRITE "", D$', "no file name"),
        ('DICT D$\nDWRITE "nofolder/x.json", D$', "cannot write nofolder/x.json"),
        ('D$ = "X"\nDWRITE "x.json", D$', "TYPE MISMATCH"),
    ]:
        rt, _ = run(source, tmp_path)
        assert rt.state == RunState.ERROR and message in rt.error.message(), (source, rt.error)


def test_failed_read_keeps_the_dict(tmp_path):
    (tmp_path / "bad.json").write_text("[1", encoding="utf-8")
    rt, out = run('ON ERROR GOTO *E\nDICT D$\nD$("K") = "V"\nDREAD "bad.json", D$\nEND\n*E\nPRINT D$("K")',
                  tmp_path)
    assert out.startswith("V")
