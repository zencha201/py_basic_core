# DESIGN.md — BASIC コア

本書は BASIC インタプリタのコア（本パッケージ）の設計書である。
言語仕様は [BASIC.md](BASIC.md)、使い方は [README.md](README.md) を参照。

- 実行基盤: Python 3.10 以降。**標準ライブラリだけを使い、外部ライブラリ（Pyxel を含む）に依存しない。**
- 使われ方: 単体で使うほか、画面を持つフロントエンド（Pyxel 版の BASIC など）の中にサブフォルダとして組み込まれる。

---

## 1. 目的と依存の規則
- 文字列で与えた BASIC プログラムを解析・実行する。画面・キーボード・ファイルには触れず、出力は Host（8）へ、入力は実行状態（6）として外へ知らせる。
- **依存の規則**
  - import するのは、パッケージ内のモジュール（相対 import）と Python の標準ライブラリだけ。自動テストで検査する（`tests/test_runtime.py`）。
  - パッケージ名は `py_basic_core`。使う側は、リポジトリのフォルダ（`py_basic_core/` の 1 つ上）を `sys.path` に入れて `import py_basic_core` とする。パッケージ内はすべて相対 import。
  - 標準ライブラリと同じ名前のモジュールを作らない（AST は `nodes.py`、命令は `instructions.py`）。誤ってパッケージのフォルダ自体が `sys.path` に入っても標準ライブラリを隠さないため。

```
（リポジトリ）
├── py_basic_core/          パッケージ
│   ├── __init__.py         公開 API（Runtime, RunState, ReplSession, BufferHost, install_standard, エラー）
│   ├── errors.py           BasicError / BasicSyntaxError / BasicRuntimeError とエラー名
│   ├── tokens.py           トークン種別・予約語
│   ├── lexer.py            字句解析
│   ├── nodes.py            AST ノード
│   ├── parser.py           構文解析（ブロックの対応を検査）
│   ├── compiler.py         AST → 命令列（ラベル解決・関数の事前登録・GLOBAL・DATA の収集）
│   ├── instructions.py     命令の定義（Instruction, CodeUnit）
│   ├── values.py           型（INT / STRING）の判定・検査・既定値
│   ├── variable.py         Scope（変数・配列・DICT）、BasicArray、BasicDict
│   ├── function.py         UserFunction / BuiltinFunction / CommandSpec / CallContext / WaitFrames
│   ├── registry.py         命令・関数の登録表
│   ├── host.py             Host インターフェースと BufferHost
│   ├── runtime.py          Runtime（VM・実行状態・中断・公開 API）
│   ├── repl.py             ReplSession（ダイレクト実行）
│   ├── stdlib/             標準関数・標準命令（11）
│   └── terminal/           文字画面のモデル（11）
├── tests/              pytest
├── BASIC.md / DESIGN.md / README.md / LICENSE
└── pytest.ini
```

---

## 2. 処理の流れ
```
ソース文字列
  → Lexer         トークン列（行番号付き。行ごとに NEWLINE、最後に EOF）
  → Parser        AST（Program: メインの文のリスト + 関数定義のリスト）
  → Compiler      CodeUnit（命令列 + ラベル表）をメイン用・関数ごとに生成
  → Runtime (VM)  命令を 1 つずつ実行（中断・再開可能）
```

## 3. Lexer（lexer.py）
- 1 行ずつ処理し、`Token(kind, value, line, column)` の列を返す。
- トークン種別: `INT` `STRING` `IDENT` `KEYWORD` `OP`（`+ - * / % = <> < <= > >= ( ) , ; :`）`LABEL`（行頭の `*名前`）`NEWLINE` `EOF`。
- 識別子とキーワードは大文字に正規化する。末尾の `$` は識別子の一部。`?` は `PRINT` として扱う。
- `REM` と `'` 以降は捨てる。

## 4. Parser（parser.py）と AST（nodes.py）
- 式は再帰下降で解析する。文は `:` と改行で区切られた流れとして読み、ブロック構文は閉じるキーワードまでを入れ子のブロックとして読む。
- 1 行 IF の THEN / ELSE 部は「行内ブロック」として読み、改行を越えない。
- ブロックが閉じていなければ開始行で、対応しない閉じキーワードはその行で構文エラーにする。
- 命令拡張の名前は `Parser(command_names=...)` として受け取り、文頭の識別子が登録済み命令ならコマンド文として解析する。
- AST ノードは `@dataclass(frozen=True)` で、行番号 `line` を持つ。
  - 式: `IntLiteral` `StringLiteral` `Name` `CallOrIndex`（配列参照か関数呼び出しかは実行時に名前解決で決める）`Unary` `Binary`
  - 文: `Assign` `Print` `Input` `If`（`branches: ((cond, body), ...)`, `else_body`）`For` `While` `Label` `Goto` `Gosub` `Return` `End` `Exit` `ExitLoop` `Dim` `DictDecl` `Erase` `Global` `Data` `Read` `Restore` `Command` `CallStatement`
  - 定義: `FunctionDef(name, params: (Param, ...), body)`、`Param(name, default=None, variadic=False)`（9）

## 5. Compiler（compiler.py）と命令（instructions.py）
AST を、スタック型 VM の命令列に変換する。
- **選んだ理由**: (1) INPUT・WAIT・命令数の上限で、式の評価中（関数呼び出しの中）でも中断・再開できる。(2) GOTO でブロックの内外へ飛ぶ動作を素直に実現できる。(3) ステップ実行などのデバッガ機能を後から足しやすい。
- `CodeUnit` はメインプログラムまたは 1 つの関数に対応し、`instructions`・`labels`（ラベル名 → 命令位置）・`global_names`（関数内で GLOBAL 宣言された名前）を持つ。各命令は元のソース行番号を持つ。
- 関数定義は最初にすべてコンパイルして登録する（前方参照）。メインの命令列には関数本体を含めない。
- AND / OR は短絡評価のため、条件付きジャンプ（`AND_JUMP` / `OR_JUMP`）に変換する。
- FOR は「開始値を代入 → 終了値と STEP を積む → `FOR_INIT` → 先頭で `FOR_CHECK`（終了判定）→ 本体 → `FOR_STEP`（加算して先頭へ）」に変換する。ループの状態（終了値・STEP）はフレームごとのループ表に、FOR 文ごとの番号で記録する（GOTO でループを抜けて再び入っても正しく動く）。
- `EXIT FOR` / `EXIT WHILE` は、コンパイル中に囲んでいるループの一覧（`UnitCompiler.loops`）から、いちばん内側の対象のループを探す。そのループの終わりへのジャンプに変換し、ジャンプ先はループを閉じるときに埋める。抜ける範囲に FOR があれば、ジャンプの前に `FOR_DROP`（その中でいちばん外側の FOR から内側のループ表を消す）を置く。
- DATA 文は命令にせず、メインプログラムの DATA の値をソース順に 1 本の表（`CompiledProgram.data`）に集める。あわせて各ラベルが表のどの位置に当たるかを記録し、`RESTORE ラベル` はその位置に読み取り位置を戻す命令に変換する。`READ` は表から次の値を取り出して代入する命令になる。読み取り位置は Runtime が持つ。
- `CONTINUE` も同じ一覧から対象のループを探し、次の回の始まり（FOR は `FOR_STEP`、WHILE は条件の評価）へのジャンプに変換する。間にあって抜ける FOR があれば `FOR_DROP` を置く。
- `SELECT CASE` は、式の値をスタックに置いたまま `CASE` の項目ごとに `CASE_MATCH`（`=` / `TO` / `IS` の比較。結果の 1 / 0 を積む）と `JUMP_IF_TRUE` を並べる。各 `CASE` の本体は `POP`（式の値を捨てる）で始まるので、本体の中は普段どおりスタックが空の状態で動く。
- **再開位置（`CodeUnit.resume_points`）**: 命令ごとに「その命令を含む文が終わる位置」を記録する。`block()` で文をコンパイルするとき、入れ子の文（ブロックの中身）を先に記録し、残り（IF / WHILE / SELECT の条件、FOR の開始値など）には文全体の終わりを記録する。`ON ERROR GOSUB` の `RETURN` 先に使う。
- 命令の一覧は `instructions.py` を参照（約 45 種）。

## 6. Runtime（runtime.py）
```python
class Runtime:
    def __init__(self, host, max_call_depth=1000): ...
    # 拡張（8）
    def register_function(self, name, fn, min_args=0, max_args=None): ...
    def register_command(self, name, fn, min_args=0, max_args=None): ...
    # 実行
    def load(self, source): ...          # プログラム全体。構文エラーは BasicSyntaxError。変数は初期化
    def load_direct(self, line): ...     # ダイレクト実行の 1 行。変数は保持
    def run(self, max_steps=10000): ...  # -> RunState
    def provide_input(self, text): ...
    def stop(self): ...
    # イベント（14）
    def call_event(self, name): ...      # -> bool
    def has_function(self, name): ...
    # 状態
    state, error, globals, functions, in_event, ended_by_end
```
- **協調実行**: 別スレッドを使わず、呼び出し側（画面のフレーム処理など）が `run(max_steps)` を繰り返し呼ぶ。`run()` は最大 `max_steps` 命令を実行して、次の実行状態を返す。

| 状態 | 意味 | 呼び出し側がすること |
|---|---|---|
| `RUNNING` | まだ続きがある | もう一度 `run()` を呼ぶ |
| `WAITING_INPUT` | INPUT で入力待ち | 入力を集め、確定したら `provide_input(text)` |
| `WAITING_FRAMES` | 命令が `WaitFrames(n)` / `WaitUntil(ready)` を返して待機中 | 1 フレームごとに `run()` を呼ぶ（1 回の呼び出しを 1 フレームと数える。`WaitUntil` は呼ぶたびに `ready()` を確かめる） |
| `FINISHED` | END / ソース終端 | 終了 |
| `EXITED` | EXIT（ダイレクト実行） | ダイレクト実行を終える |
| `STOPPED` | `stop()` が呼ばれた | — |
| `ERROR` | 実行時エラー | `error` を表示する |

- **フレーム**: 関数呼び出しごとに `Frame(code, scope, function, params, pc, stack_base, gosub_stack, loops, error_target, ...)` を積む。メインプログラムも 1 つのフレーム。VM は再帰しないので、BASIC の再帰の深さは Python の再帰上限に影響されない（上限は `max_call_depth`）。
- **値スタック**: 全フレームで 1 本。
- 1 命令の実行は「`instructions[pc]` を取り出し、命令種別 → メソッドの表で振り分ける」だけにしている。
- 実行時エラーは `BasicRuntimeError(name)` を送出し、`run()` が行番号を付けて `ERROR` 状態にする。
- Python で書かれた拡張の中で起きた予期しない例外は `ILLEGAL FUNCTION CALL` として報告し、アプリは止めない。
- **ON ERROR**（[BASIC.md](BASIC.md) 4.16）: `ON ERROR GOTO / GOSUB` は、実行したフレームに飛び先（`error_target`）と種類を記録する（`ON ERROR GOTO 0` で消す）。実行時エラーが起きたら、上のフレームから順に飛び先を持つフレームを探し、それより上のフレーム（呼び出し中の関数）を捨て、値スタックをそのフレームの開始位置まで戻して飛び先へ移る。GOSUB のときは、エラーが起きた命令（下のフレームで起きた場合はその呼び出しの命令）の再開位置を GOSUB の戻り先として積み、その `RETURN` までの間は同じフレームで次のエラーを捕まえない（エラー処理の中のエラーでくり返しにならないように）。捕まえたエラーは `last_error` に残し、`ERR$()` / `ERL()` が読む。

## 7. 変数とスコープ（variable.py）
- `Scope` は変数（名前 → 値）と配列（名前 → `BasicArray`）を持つ。グローバルスコープを 1 つ、関数呼び出しごとにローカルスコープを 1 つ作る。
- 関数内の名前解決は [BASIC.md](BASIC.md) 5.5 の順序（ローカル → 引数 → GLOBAL 宣言 → ユーザ関数 → 組み込み関数）。引数はローカルスコープとは別の辞書に入れて、この順序をそのまま実装している。
- GLOBAL 宣言は、コンパイル時に関数ごとの名前の集合として求めておき、実行時はその名前の読み書きをグローバルスコープへ回す。
- `BasicArray` は各次元の長さと平坦なリストを持ち、添字の範囲を検査する。要素数は最大 1,000,000。
- `BasicDict`（DICT。[BASIC.md](BASIC.md) 4.14）は Python の辞書でキー（文字列。数値のキーは 10 進の文字列に変換）→ 値を持ち、追加した順を保つ。配列と同じく `Scope.arrays` に入れるので、作る場所・名前解決・GLOBAL の扱いは配列と共通になる。
- かっこなしの名前が DICT を指すとき、`LOAD` は DICT そのものを積む（`COUNT(HP)` などに渡すため）。DICT 自体は値ではないので、`values.check_value` / `check_for_name` / `expect_int` が INT・STRING 以外を `TYPE MISMATCH` にし、表示・代入・演算・比較に紛れ込まないようにしている。

## 8. 拡張 API（registry.py / function.py / host.py）
**関数の登録**
```python
def abs_function(ctx, args):
    return abs(ctx.expect_int(args[0]))

runtime.register_function("ABS", abs_function, min_args=1, max_args=1)
```
- `fn(ctx, args) -> int | str`。引数の個数は登録時の指定で検査される。名前が `$` で終わる関数は STRING、それ以外は INT を返さなければならない。
- `ctx`（`CallContext`）: `expect_int(v)` / `expect_str(v)`（型検査）、`error(name, detail)`（エラーの作成）、`host`、`runtime`、`line`。

**命令の登録**
```python
def cls_command(ctx, args):
    ...
runtime.register_command("CLS", cls_command, min_args=0, max_args=1)
```
- `fn(ctx, args) -> None | WaitFrames(n) | WaitUntil(ready)`。`WaitFrames(n)` を返すと n フレーム待つ。`WaitUntil(ready, then=None)` を返すと、`ready()` が真になるまで待つ（`run()` を呼ぶたびに 1 回確かめる。GUI のメッセージボックスが閉じるまで待つ、など）。`then` を渡すと、待ち終わったときに主スレッドで呼ぶ。`then` が送出した BASIC のエラーは、その命令の行で起きたエラーとして扱う（`ON ERROR` で捕まえられる）。HTTP 命令は、裏のスレッドの結果を DICT に入れる処理と通信エラーの報告にこれを使う。
- 標準関数（`stdlib/standard_functions.py`）も、フロントエンドの命令（Pyxel 版の描画命令など）も同じ API で登録する（特別扱いしない）。
- 命令名は予約語と同じ扱いになるため、プログラムの解析より前に登録する。

**Host インターフェース（host.py）**
```python
class Host(Protocol):
    def write(self, text: str) -> None: ...   # PRINT の出力（"\n" で改行）
    def column(self) -> int: ...              # カーソルの桁（PRINT の ',' 用）
```
- 入力は Host を通さず、Runtime の `WAITING_INPUT` 状態として外へ知らせる（画面側が入力を集めて `provide_input()` で渡す）。Core は「入力が来るまで待つ」処理を持たない。
- 実装: `BufferHost`（文字列に貯める。テスト・コンソール版用）。画面を持つフロントエンドは独自の Host を作る（Pyxel 版は `terminal.TerminalBuffer` へ出力する `PyxelHost`）。

## 9. FUNCTION 拡張への備え
- 引数は `Param(name, default, variadic)` のリストで持つ。初版の Parser は `name` だけを設定する。
- 引数の束縛は `function.bind_arguments()` の 1 か所に集めた。デフォルト引数・可変長引数は、Parser の拡張とこの関数の変更で実現できる。
- ユーザ関数と組み込み関数は、共通の `min_args` / `max_args` の考え方で引数の個数を検査する。

## 10. 将来の受け口
| 機能 | 受け口 |
|---|---|
| ステップ実行・ブレークポイント | `run(max_steps=1)` と命令の行番号で実現できる |
| コンソール版 | 本パッケージに、標準入出力の Host と `run()` を回すループを組み合わせる |
| Tkinter 版 / PySide 版 | 同上。`TerminalBuffer` を各 GUI のウィジェットに描く |
| Web 版 | `run()` を少しずつ呼ぶ協調実行のためスレッド不要 |
| 標準命令の追加 | `stdlib/standard_commands.py` に `register_command` で追加 |

---

## 11. 標準関数（stdlib/）と文字画面のモデル（terminal/）
- `stdlib/`: 標準関数（[BASIC.md](BASIC.md) 6 章）を、拡張 API（8）と同じ `register_function` で登録する。`install_standard(runtime)` で一度に登録できる。
- `stdlib/dictjson.py`: DICT と JSON の変換（`nest()` / `flatten()` / `parse_json()`）。HTTP 命令と DWRITE / DREAD が同じ規則を使うために 1 か所にまとめた。
- `stdlib/dictfile.py`: DWRITE / DREAD（[BASIC.md](BASIC.md) 6.2）。ファイルを使うため `install_standard` には含めず、使うアプリが `install_dict_files(runtime, base_dir)` で登録する（`base_dir()` は相対パスの基準のフォルダを返す関数。既定は `os.getcwd`）。書き込みは一時ファイル（`ファイル名.tmp`）に書いてから `os.replace` で置き換える。読み込みは、ファイル全体を読んで変換できてから DICT を置き換える（失敗したら DICT は元のまま）。
- `stdlib/http.py`: HTTP 命令と `HTTPSTATUS()` / `HTTPBODY$()`（[BASIC.md](BASIC.md) 6.1）。プログラムがネットワークを使えるようになるため `install_standard` には含めず、使うアプリが `install_http(runtime, timeout=10)` で登録する。標準ライブラリの `urllib` / `json` / `threading` だけを使う。
  - リクエストは裏のスレッドで行い、命令は `WaitUntil(ready, then)` を返して待つ（協調実行を止めない）。結果（ステータス・本文）はスレッドが記録し、DICT への書き込みとエラーの送出は `then` が主スレッドで行う（DICT をスレッドから触らない）。
  - 送るデータ: `nest()` がキーの `.` で入れ子にして JSON にする（フォーム形式・クエリは `urlencode`）。受けたデータ: `flatten()` が JSON を `a.0.b` 形式のキーと文字列の値に平らにする（配列の要素数は `.#`）。
- `terminal/`: 画面を持つフロントエンドが共通で使える、文字画面のモデル。描画手段を持たない。
  - `TerminalBuffer`: 文字セル（全角は 2 セル）・カーソル・行末での折り返し（次の文字を書くときに折り返す）・スクロール。文字の幅は外から関数で与えられる（既定は Unicode の文字幅。フロントエンドはフォントの実際の幅を渡せる）。
  - `LineEditor`: 入力中の 1 行の編集（カーソル移動・削除）と入力履歴。

## 12. ダイレクト実行（repl.py）
- `ReplSession` は画面を持たない REPL の進行役。`start()` で `READY.` を出し、`submit(line)` で 1 行を `Runtime.load_direct()` に渡す（構文エラーはその場で表示）。実行が終わったら `finish()` がエラーと `READY.` を表示する。
- 変数はセッション中保持する（`load_direct()` は変数を初期化しない）。

## 13. テスト
- `tests/` を pytest で実行する（リポジトリのフォルダで `python -m pytest`）。`tests/conftest.py` がリポジトリのフォルダを `sys.path` に入れ、`py_basic_core` を import できるようにする。
- `test_language.py`: 言語仕様（BASIC.md の例を含む）。`test_runtime.py`: 拡張 API・中断と再開・WAIT・イベント（14）・ダイレクト実行・依存の規則。`test_terminal.py`: 文字画面のモデル。`test_http.py`: HTTP 命令（テストの中で起動するローカルのサーバを相手にする）。`test_dictfile.py`: DWRITE / DREAD（テスト用の一時フォルダを使う）。

## 14. イベント（フロントエンドから関数を呼ぶ）
GUI のボタンのクリックなど、プログラムの外で起きたことを BASIC の関数で処理するための API。文法は変えず、フロントエンド（Pyxel 版の GUI など）が使う。
```python
runtime.call_event("OK_BUTTON_CLICK")   # -> True（呼べた） / False（今は呼べない）
runtime.in_event                        # イベントの関数を実行中
runtime.ended_by_end                    # END 文で終わった（ソースの終わりで終わったときは False）
runtime.has_function("OK_BUTTON_CLICK")
```
- `call_event(name)` は引数のないユーザ関数を、イベント用のフレーム（`Frame.event`）として積む。実行は続く `run()` の呼び出しで進む。
- 呼べるのは、状態が `RUNNING`（`run()` の呼び出しの合間）、`WAITING_FRAMES`（`WAIT` 中など）、ソースの終わりで終わった `FINISHED` のとき。次のときは `False` を返し、何もしない: 関数がない・引数がある、ほかのイベントの関数を実行中、`END` やエラーで終わったあと、`INPUT` の入力待ち、呼び出しの深さが上限。
- 呼ぶ前の状態（状態・`WAIT` の残りフレーム数・`WaitUntil` の条件）を保存し、関数が戻ったらそれに戻す。`WAIT` 中に呼ばれた関数が戻ると `WAIT` の続きになり、終わったプログラムは `FINISHED` に戻る。戻り値は捨てる。
- イベントの関数の中で `END` を実行すると、プログラム全体が終わる（`ended_by_end` が真になり、以後のイベントは呼べない）。
- **ON ERROR**: イベントのフレームは境界になる。イベントの関数の中のエラーは、その関数（とそこから呼んだ関数）の `ON ERROR` だけが捕まえ、メインプログラムの `ON ERROR` には飛ばない（イベントが割り込んだ位置に飛ぶと、元の処理を壊すため）。捕まらなければ `ERROR` になる。
- `END` 命令は、`END` 文では引数 `True`、ソースの終わりに置く命令では `None` を持ち、`ended_by_end` を区別する。
