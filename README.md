# BASIC コア

行番号のいらない BASIC のインタプリタです。Python の標準ライブラリだけで動き、Pyxel などの外部ライブラリには依存しません。
画面を持たないので、コンソール・GUI・ゲームエンジンなど、いろいろなフロントエンドに組み込んで使えます。

- 言語仕様: [BASIC.md](BASIC.md)
- 設計: [DESIGN.md](DESIGN.md)

## 特徴

- INT / STRING の 2 つの型、配列（2 次元まで）、連想配列（`DICT`）、`DATA` / `READ`
- ラベルと `GOTO` / `GOSUB`、ブロック形式の `IF` / `FOR` / `WHILE`、`EXIT FOR` / `EXIT WHILE`
- 再帰呼び出しのできるユーザ定義関数、ローカル変数と `GLOBAL` 宣言
- 1 回に実行する命令数を決めて少しずつ実行できる（ゲームのフレームに合わせて動かせる。`INPUT` や待機命令で止めて再開できる）
- Python から命令・関数を追加できる（画面・入力の命令はフロントエンドが追加する）
- ダイレクト実行（REPL）、文字画面のモデル（全角対応の文字セル・折り返し・スクロール・入力行の編集）

## 使い方

パッケージは `py_basic_core/` フォルダです。リポジトリを取得し、そのフォルダ（`py_basic_core/` の 1 つ上）を `sys.path` に入れて import します。
ほかのリポジトリから使う場合は、git のサブモジュールとして取り込むと更新を追いやすくなります。

```sh
git clone https://github.com/zencha201/py_basic_core.git
```

```python
import sys
sys.path.insert(0, "py_basic_core")     # 取得したリポジトリのフォルダ

from py_basic_core import BufferHost, Runtime, RunState, install_standard

host = BufferHost()                 # PRINT の出力を文字列にためる
runtime = Runtime(host)
install_standard(runtime)           # ABS / LEFT$ / RND などの標準関数

# Python から関数を追加する
runtime.register_function("TWICE", lambda ctx, args: ctx.expect_int(args[0]) * 2, 1, 1)

runtime.load('INPUT "NAME";N$\nPRINT "HELLO, ";N$;TWICE(21)')
while True:
    state = runtime.run(10000)       # 最大 10000 命令ずつ実行
    if state == RunState.WAITING_INPUT:
        runtime.provide_input("TARO")
    elif state != RunState.RUNNING:
        break
print(host.output)                  # NAME? HELLO, TARO42
```

画面に出すフロントエンドは、`Host`（`write` / `column`）を自分で作り、`terminal.TerminalBuffer` に出力すると便利です。

## フォルダ構成

| パス | 内容 |
|---|---|
| `py_basic_core/` | パッケージ |
| `py_basic_core/lexer.py` `parser.py` `nodes.py` `compiler.py` `instructions.py` `runtime.py` | 字句解析 → 構文解析 → 命令列 → 実行 |
| `py_basic_core/values.py` `variable.py` `function.py` `registry.py` `host.py` `errors.py` `tokens.py` | 型・変数・関数・拡張の登録表・出力先・エラー・予約語 |
| `py_basic_core/repl.py` | ダイレクト実行 |
| `py_basic_core/stdlib/` | 標準関数 |
| `py_basic_core/terminal/` | 文字画面のモデル |
| `tests/` | テスト |
| `BASIC.md` / `DESIGN.md` | 言語仕様 / 設計 |

## テスト

```sh
pip install pytest
python -m pytest        # リポジトリのフォルダで実行
```

## ライセンス

MIT License（[LICENSE](LICENSE)）
