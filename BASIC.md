# BASIC.md — BASIC 言語仕様

本書は BASIC コアが実行する BASIC 言語（以下「本 BASIC」）の仕様である。
処理系の設計は [DESIGN.md](DESIGN.md)、使い方は [README.md](README.md) を参照。

- 版: 0.1

---

## 1. 基本規則

### 1.1 文字と大文字小文字
- ソースは Unicode 文字列（エディタで編集中のテキストやファイルの内容）。
- **キーワード・変数名・関数名・ラベル名は大文字小文字を区別しない。** 内部では大文字に正規化する（`score` と `SCORE` は同じ変数）。
- 文字列リテラルの中身は区別する（`"Hello"` はそのまま）。

### 1.2 行と文
- 1 行に 1 つ以上の文を書く。`:` で区切って複数の文を並べられる。
  ```basic
  A=1:B=2:PRINT A+B
  ```
- 行番号は使わない（ラベルで代替する。4.1）。
- 空行は無視する。行頭・文の前後の空白とタブは無視する（字下げは自由）。
- 1 つの文を複数行に分けて書く手段（行継続）はない。

### 1.3 コメント
```basic
REM これはコメント
' これもコメント
A=1 ' 文の後ろにも書ける
```
- `REM` / `'` から行末までを無視する（`:` も含めて無視）。

### 1.4 識別子（変数名・関数名・ラベル名）
- 英字または `_` で始まり、英字・数字・`_` が続く。**長さの制限なし。**
- 文字列型の変数・文字列を返す関数は末尾に `$` を付ける（2.2）。
- キーワード（付録 A）と、登録済みの命令名（6章）は変数名に使えない。
- 例: `PLAYER_HP` `ENEMY_COUNT` `NAME$` `_TMP1`

---

## 2. 型と値

### 2.1 型
サポートする型は次の 2 つのみ。

| 型 | 内容 | リテラルの例 |
|---|---|---|
| INT | 整数 | `0` `123` `-5`（`-` は単項演算子） |
| STRING | 文字列 | `"HELLO"` `""` `"日本語"` |

- INT の範囲: **制限なし**。
- 文字列リテラル内で `"` を書くときは `""` と重ねる（`PRINT "A""B"` → `A"B`）。
- 実数（小数）・論理型はない。真偽は INT で表す（2.4）。

### 2.2 変数の型
- **変数名の末尾が `$` なら STRING 型、それ以外は INT 型。**
- `A` と `A$` は別の変数。
- 型の合わない代入は実行時エラー（`A="X"` → `TYPE MISMATCH`）。
- 宣言は不要。初めて代入したときに作られる。
- 代入前の変数を参照した場合: **INT は 0、STRING は `""`**（エラーにしない）。

### 2.3 型変換
自動変換は行わない。変換は関数で行う。
```basic
A$=STR$(123)    ' "123"
B=VAL("45")     ' 45
```

### 2.4 真偽値
- 条件式は INT で評価し、**0 が偽、0 以外が真**。
- 比較演算・論理演算の結果は **真=1 / 偽=0**。

---

## 3. 式

### 3.1 演算子と優先順位（高い順）
| 順位 | 演算子 | 説明 | 結合 |
|---|---|---|---|
| 1 | `( )` | 括弧・関数呼び出し・配列参照 | — |
| 2 | `-` `+`（単項） | 符号 | 右 |
| 3 | `*` `/` `%` | 乗算・除算・剰余 | 左 |
| 4 | `+` `-` | 加算・減算（`+` は文字列の連結も行う） | 左 |
| 5 | `=` `<>` `<` `<=` `>` `>=` | 比較 | 左（連鎖は非推奨） |
| 6 | `NOT` | 論理否定 | 右 |
| 7 | `AND` | 論理積 | 左 |
| 8 | `OR` | 論理和 | 左 |

### 3.2 算術演算
- INT 同士のみ。STRING を含むと `TYPE MISMATCH`（`+` の文字列連結を除く）。
- `/` は整数除算。**0 方向への切り捨て**（`-7/2` → `-3`）。
- `%` は剰余。**結果の符号は左辺に合わせる**（`-7%2` → `-1`。`/` と `A = (A/B)*B + A%B` が成り立つ）。
- 0 で割ると `DIVISION BY ZERO`。

### 3.3 文字列演算
- `+` で連結（`"AB"+"C"` → `"ABC"`）。STRING と INT の連結は `TYPE MISMATCH`。

### 3.4 比較演算
- INT 同士は数値比較、STRING 同士は文字コード順（辞書順）で比較する。
- INT と STRING の比較は `TYPE MISMATCH`。
- `=` は文脈で代入と比較を区別する（文頭の `変数=` は代入、それ以外は比較）。

### 3.5 論理演算
- `AND` `OR` `NOT` は**論理演算**（ビット演算ではない）。結果は 1 / 0。
- `AND` `OR` は**短絡評価**する（左辺で結果が決まれば右辺を評価しない）。

---

## 4. 文（ステートメント）

### 4.1 ラベル・GOTO・GOSUB・RETURN
```basic
*START
PRINT "LOOP"
GOTO START

GOSUB SUB1
END

*SUB1
PRINT "IN SUB"
RETURN
```
- ラベル定義は行頭の `*名前`。その行には他の文を続けて書いてもよい（`*L1:PRINT 1`）。
- 飛び先は `GOTO 名前` / `GOSUB 名前`。`*` を付けた `GOTO *名前` も可。
- 同じ名前のラベルを 2 回定義すると構文エラー。存在しないラベルへのジャンプは構文エラー（実行前に検出する）。
- **ラベルの有効範囲:** メインプログラムのラベルはメインプログラム内、関数内のラベルはその関数内でのみ有効。関数の内外をまたぐ GOTO / GOSUB はできない。
- `RETURN` は直近の `GOSUB` の次の文へ戻る。GOSUB していない状態の `RETURN`（関数外）は `RETURN WITHOUT GOSUB`。
- GOTO でブロック（IF / FOR / WHILE）の内外へ飛ぶことは許可する（ブロックの途中から実行が続く）。整合性は利用者の責任とする。

### 4.2 代入
```basic
A=10
NAME$="TARO"
MAP(3,4)=1
```
- `LET` キーワードは使えるが省略可能。

### 4.3 PRINT
```basic
PRINT "A=";A        ' A=10
PRINT 1,2           ' 次の桁区切りへ進めて表示
PRINT "NO NEWLINE"; ' 改行しない
PRINT               ' 空行
```
- `;` は間を空けずに続けて表示、`,` は次の 8 桁区切り位置まで空白を入れる。
- 末尾が `;` または `,` の場合は改行しない。
- 数値の前後に空白は付けない。
- `?` は `PRINT` の省略形として使える。

### 4.4 INPUT
```basic
INPUT NAME$
INPUT "NAME";NAME$
```
- 画面内でインライン入力する（ダイアログは使わない）。`? ` を表示し、その後ろに入力文字を表示する。
- プロンプト文字列を指定した場合は `NAME? ` のように表示する。
- `Enter` で確定。`Backspace` で 1 文字削除。日本語入力（IME の確定文字列）も受け付ける。
- 変数 1 つにつき 1 回の入力。INT 変数に数値以外が入力されたら `?REDO` を表示して入力をやり直す。
- 空のまま確定した場合: INT は 0、STRING は `""`。

### 4.5 IF
4 つの書き方をサポートする。

**ブロック形式**
```basic
IF A=1 THEN
    PRINT "ONE"
ELSIF A=2 THEN
    PRINT "TWO"
ELSE
    PRINT "OTHER"
ENDIF
```

**THEN 省略（ブロック形式）**
```basic
IF A=1
    PRINT "A"
ENDIF
```

**1 行 IF / 1 行 IF-ELSE**
```basic
IF A=1 THEN PRINT "A"
IF A=1 THEN PRINT "A" ELSE PRINT "B"
IF A=1 THEN PRINT "A":B=2 ELSE PRINT "B":B=3
```

- 判定規則:
  - `IF 条件` または `IF 条件 THEN` で**行（または `:` 区切りの文）が終わる** → ブロック形式。`ENDIF` まで。
  - `THEN` の後ろに文が続く → 1 行 IF。その行の終わりまでが対象。
- 1 行 IF では `THEN` の後ろの `:` 区切りの文はすべて THEN 側、`ELSE` の後ろはすべて ELSE 側。
- `ELSIF 条件` の `THEN` も省略可能。
- `END IF`（空白入り）も `ENDIF` と同じ扱い。
- 1 行 IF の中にブロック形式の IF は書けない。1 行 IF の入れ子（`IF A THEN IF B THEN PRINT 1`）は可。

### 4.6 FOR / NEXT
```basic
FOR I=1 TO 10
    PRINT I
NEXT

FOR I=10 TO 0 STEP -2
    PRINT I
NEXT I
```
- `STEP` 省略時は 1。STEP に 0 を指定すると実行時エラー。
- `NEXT` / `NEXT I` / `NEXT INDEX` は**すべて同じ**。変数名は書いても無視する（直近の FOR に対応する）。
- 判定は**ループの先頭**で行う（開始値が終了値を超えていれば 1 回も実行しない）。
- 終了値と STEP はループ開始時に 1 回だけ評価する。
- ループ終了後の変数値は「最後の値 + STEP」。
- ループ変数は INT 変数のみ（配列要素は不可）。
- `EXIT FOR` で、途中でループを抜けて `NEXT` の次へ進む（4.7.1）。

### 4.7 WHILE / WEND
```basic
WHILE A<10
    A=A+1
WEND
```
- 先頭で条件を評価し、偽なら `WEND` の次へ進む。
- `EXIT WHILE` で、途中でループを抜けて `WEND` の次へ進む（4.7.1）。

### 4.7.1 EXIT FOR / EXIT WHILE
```basic
FOR I=1 TO 100
    IF A(I)=0 THEN EXIT FOR
NEXT
PRINT "見つかった位置: ";I

WHILE 1
    INPUT "コマンド";C$
    IF C$="Q" THEN EXIT WHILE
WEND
```
- 書いた位置を囲んでいる、いちばん内側の FOR（または WHILE）を抜ける。間に別の種類のループがあれば、それもまとめて抜ける（例: FOR の中の WHILE の中で `EXIT FOR` を実行すると、WHILE と FOR の両方を抜ける）。
- `EXIT FOR` で抜けたときのループ変数は、抜けた時点の値のまま（STEP は足さない）。
- 囲んでいるループがなければ構文エラー（`EXIT FOR WITHOUT FOR` / `EXIT WHILE WITHOUT WHILE`）。ループの外にある GOSUB 先や関数の中からは、呼び出し元のループを抜けられない。
- 単独の `EXIT` はダイレクト実行の終了命令（8.2）で、プログラムの中では構文エラーのまま。
- 1 行 IF の THEN の後ろでは、`:` で続く文も THEN 側になる（4.5）。`FOR I=1 TO 9:IF I=3 THEN EXIT FOR:NEXT` の `NEXT` は THEN 側に入ってしまうので、`IF` と `NEXT` は別の行に書く。

### 4.7.2 CONTINUE / CONTINUE FOR / CONTINUE WHILE
```basic
FOR I=1 TO 10
    IF I%2=0 THEN CONTINUE      ' 偶数は飛ばす
    PRINT I
NEXT
```
- ループの残りを飛ばして、次の回に進む。FOR は `NEXT` と同じく STEP を足して終了を判定し、WHILE は条件の判定に戻る。
- `CONTINUE` は、書いた位置を囲んでいるいちばん内側のループ（FOR でも WHILE でも）を対象にする。`CONTINUE FOR` / `CONTINUE WHILE` は、いちばん内側のその種類のループを対象にし、間にある別の種類のループは抜ける（例: FOR の中の WHILE の中で `CONTINUE FOR` を実行すると、WHILE を抜けて FOR の次の回へ進む）。
- 囲んでいるループがなければ構文エラー（`CONTINUE WITHOUT LOOP` / `CONTINUE FOR WITHOUT FOR` / `CONTINUE WHILE WITHOUT WHILE`）。
- 1 行 IF の注意は `EXIT FOR` と同じ（4.7.1）。

### 4.8 END
- プログラムの実行を終了する。関数の中で実行しても終了する。
- ソースの終端に達した場合も終了する（`END` は省略可能）。
- `END FUNCTION` / `END IF` は別の文（4.5 / 5.1）。

### 4.9 DIM（配列）
```basic
DIM A(10)
A(0)=100
DIM MAP(32,32)
DIM NAMES$(5)
```
- **最大 2 次元。添字は 0 始まり。**
- `DIM A(10)` の要素数: **0〜10 の 11 個**（従来の BASIC と同じ）。
- 要素の初期値は INT 配列が 0、STRING 配列が `""`。
- 範囲外の添字は `SUBSCRIPT OUT OF RANGE`。
- 同じ名前の配列を 2 回 DIM すると `REDIM`（実行時エラー）。
- DIM していない配列の参照・代入はエラー（自動作成しない）。
- 配列と同名の単純変数は共存できない（`A` と `A(0)` は同時に使えない）。
- 1 文で複数宣言できる: `DIM A(10),B$(5)`。

### 4.10 GLOBAL
5.4 を参照。

### 4.11 命令拡張の文
Python 側から登録した命令（7 章）は次の形で呼ぶ。
```basic
CLS 0
TEXT 10,10,"HELLO",7
```
- `命令名 式, 式, ...`（引数なしも可）。引数の個数・型は命令ごとに検査する。

### 4.12 ユーザ関数の呼び出し文
戻り値を使わない関数は文として呼べる。戻り値は捨てる。
```basic
ADD_SCORE(10)
```

### 4.13 DATA / READ / RESTORE
プログラムの中に値を並べておき、順に読み込む。
```basic
FOR I=1 TO 3
    READ NAME$,HP
    PRINT NAME$;" ";HP
NEXT
RESTORE BOSS
READ NAME$,HP
PRINT "BOSS: ";NAME$
END

DATA "SLIME",5,"BAT",3,"GHOST",8
*BOSS
DATA "DRAGON",99
```
- `DATA 値, 値, ...`: 整数（`-5` のような符号付きも可）と文字列（`"..."`）を並べる。実行しても何もしない。引用符のない文字列（`DATA ABC`）は使えない。
- `READ 変数, 変数, ...`: 次の DATA の値を順に読み込む。配列の要素にも読める（`READ A(I)`）。
- `RESTORE`: 読む位置を最初の DATA に戻す。`RESTORE ラベル` はそのラベルより後にある最初の DATA に戻す（`RESTORE *ラベル` も可）。
- 読む順番は、ソースの上から下への DATA の並び順。DATA はどこに書いてもよい（IF などのブロックの中でも、実行されない場所でも数える）。
- 型が合わなければ `TYPE MISMATCH`（例: 文字列の値を `READ A` で読む）。値が残っていなければ `OUT OF DATA`。
- 関数の中でも `READ` / `RESTORE` を使える（メインプログラムの DATA を読む）。関数の中に `DATA` は書けない（構文エラー）。
- ダイレクト実行では、その行の DATA だけを読む。

### 4.14 DICT（連想配列）
数値の添字の代わりに、文字列や数値を「キー」にして値をしまう。
```basic
DICT HP, JOB$            ' 作る（値の型は名前の $ で決まる。HP は INT、JOB$ は STRING）
HP("SLIME")=5            ' 書く（キーがなければ追加、あれば上書き）
HP(1)=3                  ' 数値のキー。HP("1") と同じキー
JOB$("TARO")="WARRIOR"
PRINT HP("SLIME")        ' 読む

IF HASKEY(HP,"SLIME") THEN PRINT "いる"
FOR I=0 TO COUNT(HP)-1   ' 全部のキーを順に（追加した順）
    K$=KEY$(HP,I)
    PRINT K$;" ";HP(K$)
NEXT
ERASE HP("SLIME")        ' 1 つ消す
ERASE HP                 ' 全部消す
```
| 操作 | 書き方 | 説明 |
|---|---|---|
| 作る | `DICT 名前, 名前, ...` | 空の DICT を作る。同じ名前を 2 回作ると `REDIM`。同じ名前の変数・配列とは共存できない |
| 書く / 読む | `HP(キー)=値` / `HP(キー)` | キーは 1 つだけ。ないキーを読むと 0 / `""`（エラーにしない） |
| キーがあるか | `HASKEY(HP, キー)` | 1 / 0 |
| 数 | `COUNT(HP)` | 登録されているキーの数 |
| i 番目のキー | `KEY$(HP, i)` | i は 0 から。追加した順。範囲外は `SUBSCRIPT OUT OF RANGE` |
| 消す | `ERASE HP(キー)` / `ERASE HP` | 1 つ / 全部。ないキーを消してもエラーにしない。`ERASE A, B(1)` のように並べられる |

- **キー**: 文字列か数値。数値は 10 進の文字列として扱う（`HP(1)` と `HP("1")` は同じキー、`HP("01")` は別のキー）。`KEY$` は文字列で返す。
- **DICT 自体を渡す**: `HASKEY` `COUNT` `KEY$` には、かっこを付けずに名前だけを書く（`COUNT(HP)`）。DICT 自体は値ではないので、`PRINT HP` や `X=HP` は `TYPE MISMATCH`。
- `INPUT HP("A")`、`READ HP(K$)` のように、DICT の要素にも入力・読み込みができる。
- **スコープ**: 配列と同じ。関数の中で作った DICT はその関数の中だけで使え、外の DICT は `GLOBAL HP` で使う。DICT を関数の引数として渡すことはできない。
- 普通の配列に文字列の添字を使うと `TYPE MISMATCH`（`DIM A(3)` に対する `A("X")`）。

### 4.15 SELECT CASE
```basic
SELECT CASE SCORE
CASE 100
    PRINT "PERFECT"
CASE 80 TO 99
    PRINT "GOOD"
CASE 50, 60, 70
    PRINT "OK"
CASE IS < 50
    PRINT "TRY AGAIN"
CASE ELSE
    PRINT "?"
END SELECT
```
- `SELECT CASE 式` の値（INT でも STRING でもよい）を、上の `CASE` から順に調べ、最初に当てはまった `CASE` の文だけを実行して `END SELECT` の次へ進む。当てはまる `CASE` がなく `CASE ELSE` もなければ何もしない。
- `SELECT CASE` の式は最初に 1 回だけ評価する。
- `CASE` に書けるもの（`,` で区切って並べると「どれか 1 つに当てはまれば」）:

| 書き方 | 当てはまる条件 |
|---|---|
| `CASE 値` | 式 = 値 |
| `CASE 値1 TO 値2` | 値1 ≦ 式 ≦ 値2 |
| `CASE IS 比較演算子 値` | 式 比較演算子 値（`IS < 50`、`IS <> 0` など。`=` `<>` `<` `<=` `>` `>=`） |
| `CASE ELSE` | ほかのどれにも当てはまらない（最後の `CASE` として 1 つだけ書ける） |

- 式と値の型が違えば `TYPE MISMATCH`（STRING どうしは文字コード順で比べる）。
- `SELECT CASE` と最初の `CASE` の間に文は書けない。`END SELECT` がなければ `SELECT WITHOUT END SELECT`。
- `:` で区切って 1 行に書ける（`CASE 1: PRINT "ONE"`）。1 行 IF の THEN / ELSE の後ろには書けない。
- `IS` は `CASE` の中でだけ意味を持つ（予約語ではない）。

### 4.16 ON ERROR GOTO / ON ERROR GOSUB
実行時エラー（9 章）が起きたときに、プログラムを止めずにラベルへ移る。
```basic
ON ERROR GOTO HANDLER
INPUT "数";N
PRINT 100/N
END
*HANDLER
PRINT "エラー: ";ERR$();"（";ERL();"行）"
```
```basic
ON ERROR GOSUB WARN       ' エラーが起きたら WARN を呼び、その後は次の文から続ける
X=1/0
PRINT "続き"
END
*WARN
PRINT "注意: ";ERR$()
RETURN
```
| 文 | 動き |
|---|---|
| `ON ERROR GOTO ラベル` | エラーが起きたら、そのラベルへ移る（GOTO と同じ） |
| `ON ERROR GOSUB ラベル` | エラーが起きたら、そのラベルを GOSUB で呼ぶ。`RETURN` で、エラーが起きた文の次の文から続ける |
| `ON ERROR GOTO 0` | エラー処理をやめる（以後のエラーではプログラムが止まる） |

- **エラーの内容**: `ERR$()` がエラーの名前（例: `"DIVISION BY ZERO"`）、`ERL()` が行番号を返す（6 章）。
- **捕まえるもの**: 実行時エラーだけ。構文エラー（実行前に見つかるもの）と、フロントエンドからの中断（`stop()`）は捕まえない。
- **有効な範囲**: `ON ERROR` を実行したメインプログラム（または関数）の中と、そこから呼んだ関数の中で起きたエラー。関数の中で起きたエラーを外側のメインプログラムの `ON ERROR` が捕まえたときは、その関数（と途中の呼び出し）は打ち切られる。関数の中で実行した `ON ERROR` は、その関数を抜けると無効になる。ラベルは `ON ERROR` を書いたメインプログラム（または関数）の中のもの。
- **「次の文」**: `:` で区切った同じ行の次の文も含む。IF / WHILE / SELECT CASE の条件の評価中、FOR の開始値などの評価中に起きたエラーでは、その IF / WHILE / SELECT CASE / FOR 全体の次の文になる。
- **エラー処理の中のエラー**: `ON ERROR GOSUB` で呼んだサブルーチンの中（`RETURN` するまで）で起きたエラーでは、プログラムが止まる。`ON ERROR GOTO` で移った先で起きたエラーは、もう一度同じラベルへ移る（何度もエラーになる処理はくり返しになるので注意）。
- `ERROR` は `ON ERROR` の中でだけ意味を持つ（予約語ではない）。

---

## 5. ユーザ定義関数

### 5.1 定義
```basic
FUNCTION ADD(A,B)
    RETURN A+B
END FUNCTION

FUNCTION GREET$(NAME$)
    RETURN "HELLO "+NAME$
END FUNCTION
```
- `FUNCTION 名前(引数, ...)` 〜 `END FUNCTION`。引数なしは `FUNCTION F()`。
- 関数定義はプログラムのどこに書いてもよい。実行時に関数定義に到達した場合は、その定義を飛ばして `END FUNCTION` の次から続ける。
- 関数の中で関数を定義することはできない。
- 同じ名前の関数を 2 回定義すると構文エラー（`DUPLICATE FUNCTION`）。
- 組み込み関数と同じ名前の関数を定義すると、ユーザ定義関数が優先される（5.5 の順序）。
- 引数の型は引数名の `$` で決まる。呼び出し時に型が合わなければ `TYPE MISMATCH`、個数が合わなければ `ARGUMENT COUNT MISMATCH`。
- 戻り値: `RETURN 式` で返す。`RETURN` 単独（関数内で GOSUB していない場合）、または `END FUNCTION` に達したら、関数名に `$` があれば `""`、なければ 0 を返す。
- 関数内の `GOSUB` で呼んだサブルーチンからは、値なしの `RETURN` で戻る。
- 関数名の `$` と戻り値の型が合わない場合は `TYPE MISMATCH`。

### 5.2 前方参照・再帰
- **前方参照可。** 実行前にプログラム全体を解析し、すべての関数定義を先に登録する。
  ```basic
  PRINT ADD(1,2)
  FUNCTION ADD(A,B)
      RETURN A+B
  END FUNCTION
  ```
- **再帰呼び出し可。**
  ```basic
  FUNCTION FACT(N)
      IF N<=1 THEN RETURN 1
      RETURN N*FACT(N-1)
  END FUNCTION
  ```
- 呼び出しの深さの上限: 1000（設定ファイルの `basic_max_call_depth` で変更可）。超えると `STACK OVERFLOW`。

### 5.3 スコープ
- 関数内で作られた変数・配列は**ローカル**。関数を抜けると消える。呼び出しごとに別の領域を持つ（再帰しても干渉しない）。
- 引数もローカル（値渡し。関数内で書き換えても呼び出し元には影響しない）。
- 配列は引数として渡せない。

### 5.4 GLOBAL 宣言
関数内でグローバル変数を使う場合は**明示宣言が必須**。
```basic
SCORE=0
FUNCTION ADD_SCORE(V)
    GLOBAL SCORE
    SCORE=SCORE+V
END FUNCTION

GLOBAL SCORE,HP,MP      ' 複数宣言
GLOBAL MAP              ' 配列も同じ書き方
```
- 宣言がない名前はローカルとして扱う。
  ```basic
  VALUE=100
  FUNCTION TEST()
      VALUE=200          ' ローカル変数 VALUE を作る
  END FUNCTION
  ' グローバルの VALUE は 100 のまま
  ```
- `GLOBAL` は関数内でのみ使える（関数外では構文エラー）。
- 宣言の効果はその関数全体に及ぶ（関数内で宣言より前にある参照もグローバルを指す）。宣言は関数の先頭に書くことを推奨する。
- 引数と同じ名前を GLOBAL 宣言すると構文エラー。
- 宣言した時点でグローバル変数が存在しなければ、初期値（0 / `""`）で作る。

### 5.5 名前解決の順序
関数内で `名前` や `名前(...)` を参照したとき、次の順に探す。

1. ローカル変数（ローカル配列を含む）
2. 引数
3. GLOBAL 宣言された変数
4. ユーザ定義関数
5. 組み込み関数（標準関数・Python から登録した関数）

- 関数外（メインプログラム）では「グローバル変数 → ユーザ定義関数 → 組み込み関数」の順。
- `名前(...)` が配列としても関数としても見つからなければ `UNDEFINED FUNCTION`。
- 括弧なしの `名前` は変数として扱う（引数なし関数の呼び出しは `F()` と書く）。

---

## 6. 標準関数

| 関数 | 説明 | 例 |
|---|---|---|
| `ABS(n)` | 絶対値 | `ABS(-3)` → 3 |
| `MIN(a,b,...)` | 最小値（2 個以上） | `MIN(3,1,2)` → 1 |
| `MAX(a,b,...)` | 最大値（2 個以上） | `MAX(3,1,2)` → 3 |
| `LEN(s$)` | 文字数（全角も 1 文字） | `LEN("ABC")` → 3 |
| `LEFT$(s$,n)` | 先頭から n 文字 | `LEFT$("ABCDE",2)` → `"AB"` |
| `RIGHT$(s$,n)` | 末尾から n 文字 | `RIGHT$("ABCDE",2)` → `"DE"` |
| `MID$(s$,start[,n])` | start 文字目から n 文字（n 省略時は末尾まで）。**start は 1 始まり**（従来の BASIC と同じ） | `MID$("ABCDE",2,3)` → `"BCD"` |
| `STR$(n)` | 数値を文字列に | `STR$(-5)` → `"-5"` |
| `VAL(s$)` | 文字列を数値に。先頭の空白を無視し、先頭の符号と数字の並びだけを読む。読めなければ 0 | `VAL("12AB")` → 12 |
| `RND(n)` | 0〜n-1 の乱数（n は 1 以上） | `RND(6)+1` → 1〜6 |
| `CHR$(n)` | 文字コード n の文字 | `CHR$(65)` → `"A"` |
| `ASC(s$)` | 先頭の文字の文字コード（空文字列はエラー） | `ASC("A")` → 65 |
| `INSTR(s$,t$)` | s$ の中で t$ が始まる位置（1 始まり）。なければ 0 | `INSTR("HELLO","LL")` → 3 |
| `HASKEY(d,key)` | DICT d にキーがあれば 1、なければ 0（4.14） | `HASKEY(HP,"SLIME")` |
| `COUNT(d)` | DICT d のキーの数 | `COUNT(HP)` |
| `KEY$(d,i)` | DICT d の i 番目（0 から、追加した順）のキー | `KEY$(HP,0)` |
| `ERR$()` | `ON ERROR` で捕まえたエラーの名前（まだなければ `""`）（4.16） | `"DIVISION BY ZERO"` |
| `ERL()` | `ON ERROR` で捕まえたエラーの行番号（まだなければ 0） | `ERL()` → 12 |

- 引数の個数・型が合わなければ実行時エラー（`ARGUMENT COUNT MISMATCH` / `TYPE MISMATCH`）。LEFT$ などで n が負なら `ILLEGAL FUNCTION CALL`、文字数を超える n は末尾までとする。

### 6.1 HTTP / HTTPS のリクエスト（HTTP 命令）
Web の API などに HTTP / HTTPS でリクエストを送り、返ってきた JSON を DICT で受け取る。
アプリが `install_http(runtime)` で登録したときだけ使える（ネットワークを使うため、`install_standard` には含めない。[DESIGN.md](DESIGN.md) 8）。

```basic
DICT REQ$, RES$
REQ$("name") = "TARO"
REQ$("profile.age") = "20"        ' "." で入れ子: {"name":"TARO","profile":{"age":"20"}}
HTTP "POST", URL$, REQ$, RES$
IF HTTPSTATUS() = 200 THEN PRINT RES$("user.id"); " "; RES$("items.#")
```

| 命令・関数 | 説明 |
|---|---|
| `HTTP method$, url$, data, reply$[, headers$]` | リクエストを送り、返事が来るまで待つ（待つ間も画面は動き、中断できる） |
| `HTTPSTATUS()` | 直前の `HTTP` のステータスコード（200、404 など。まだなければ 0、通信できなかったときも 0） |
| `HTTPBODY$()` | 直前の `HTTP` の返事の本文そのまま（JSON でないときなど） |

- **method$**: `GET` `POST` `PUT` `PATCH` `DELETE` `HEAD` など（大文字・小文字は問わない）。英字以外を含むと `ILLEGAL FUNCTION CALL`。
- **url$**: `http://` か `https://` で始まる URL。それ以外（`""` を含む）は `ILLEGAL FUNCTION CALL`。
- **data**（送るデータ）: DICT か、送るものがなければ `""`。
  - `GET` `DELETE` `HEAD` では URL のクエリ（`?name=TARO&page=2`）にする。
  - それ以外では本文にする。既定は JSON。キーの `.` は入れ子のオブジェクトになる（`"a"` と `"a.b"` のように重なると `ILLEGAL FUNCTION CALL`）。値は INT の DICT なら数値、STRING の DICT なら文字列。
  - headers$ の `Content-Type` が `application/x-www-form-urlencoded` のときは、フォーム形式（`name=TARO&memo=a%26b`。キーはそのまま）で送る。
- **reply$**（受ける DICT）: STRING の DICT（そうでなければ `TYPE MISMATCH`）。返事が来たら中身を空にしてから、JSON のオブジェクトか配列なら、平らにして入れる。JSON でなければ空のまま。

| JSON | DICT |
|---|---|
| `{"user":{"name":"TARO"}}` | `RES$("user.name")` = `"TARO"` |
| `{"items":[{"id":5},{"id":7}]}` | `RES$("items.0.id")` = `"5"`、`RES$("items.1.id")` = `"7"`、`RES$("items.#")` = `"2"`（配列の要素数） |
| 数値 / `true` `false` / `null` | `"5"` `"3.14"`（`VAL()` で INT に。小数は文字列のまま） / `"1"` `"0"` / `""` |
| 返事全体が配列 `[...]` | `RES$("0.id")`、`RES$("#")` |

- **headers$**（省略可）: 送るヘッダの STRING の DICT（`H$("Authorization") = "Bearer ..."` など）。`Content-Type`（本文が JSON のとき）と `Accept` は、指定しなければ自動で付ける。
- **エラー**: 404 や 500 などの返事はエラーにしない（`HTTPSTATUS()` で調べる。本文が JSON なら reply$ に入る）。つながらない・タイムアウト（10 秒）・返事が大きすぎる（4MB まで）ときは `NETWORK ERROR`（`ON ERROR` で捕まえられ、`ERR$()` は `"NETWORK ERROR"`）。このとき reply$ は空になる。
- 名前の `.` を含む JSON のキーは、入れ子と区別できない（`{"a.b":1}` も `RES$("a.b")` になる）。
- スレッドを使えない環境（Web ブラウザなど）では `NETWORK ERROR` になる。

---

## 7. 画面・入力の命令（フロントエンドごと）

本パッケージ（BASIC コア）は画面を持たないので、描画・キー入力などの命令と関数は持たない。
画面を持つフロントエンドが、拡張 API（[DESIGN.md](DESIGN.md) 8）で命令・関数を登録して提供する。
命令名・関数名・引数の書き方は、4.11（命令拡張の文）と 6 章（関数）の規則に従う。

- Pyxel 版（[pyxel_basic_runtime](https://github.com/zencha201/pyxel_basic_runtime)）の命令・関数は、[COMMANDS.md](https://github.com/zencha201/pyxel_basic_runtime/blob/main/COMMANDS.md) を参照（`CLS` `TEXT` `LINE` `PSET` `RECT` `CIRC` `LOAD` `BLT` `IMGSET` `MOUSE` `WAIT`、`PGET` `BTN` `BTNP` `INKEY$` `MOUSEX` `MOUSEY` `SCREENW` `SCREENH`）。

---

## 8. 実行モード
どちらの実行モードを、どのキーやメニューで始めるかはフロントエンドが決める（Pyxel 版のエディタでは F5 / F6）。

### 8.1 プログラム実行
- プログラム全体を実行する（`Runtime.load(source)`）。変数は空の状態から始まる。
- 実行前に全体を解析し、構文エラーがあれば実行せずにエラーを報告する。
- `END` またはソース終端で終了する。

### 8.2 ダイレクト実行
- REPL モード。`READY.` を表示し、1 行ずつ入力して実行する（`ReplSession`）。
- 1 行に `:` 区切りで複数の文を書ける。ブロック構文（IF / FOR / WHILE）は**1 行に収まる範囲でのみ**使える（`FOR I=1 TO 3:PRINT I:NEXT`）。
- `FUNCTION` の定義はダイレクト実行では行えない（`NOT ALLOWED IN DIRECT MODE`）。
- 変数はダイレクト実行のセッション中保持する。
- 1 行の実行が終わるたびに `READY.` を表示する。エラーが出てもセッションは続く（エラーには行番号を付けない）。
- `EXIT` でダイレクト実行を終える。

### 8.3 中断
- 実行中・入力待ちの BASIC は、フロントエンドが `Runtime.stop()` を呼ぶと止まる（`STOPPED`）。どのキーで止めるかはフロントエンドが決める。

---

## 9. エラー

### 9.1 種類
| 区分 | 検出時期 | 例 |
|---|---|---|
| 構文エラー | 実行前（解析時） | `SYNTAX ERROR`、`UNTERMINATED STRING`、`UNDEFINED LABEL`、`DUPLICATE LABEL`、`DUPLICATE FUNCTION`、`IF WITHOUT ENDIF`、`ENDIF WITHOUT IF`、`ELSE WITHOUT IF`、`ELSIF WITHOUT IF`、`FOR WITHOUT NEXT`、`NEXT WITHOUT FOR`、`WHILE WITHOUT WEND`、`WEND WITHOUT WHILE`、`FUNCTION WITHOUT END FUNCTION`、`END FUNCTION WITHOUT FUNCTION`、`EXIT FOR WITHOUT FOR`、`EXIT WHILE WITHOUT WHILE`、`CONTINUE WITHOUT LOOP`、`CONTINUE FOR WITHOUT FOR`、`CONTINUE WHILE WITHOUT WHILE`、`SELECT WITHOUT END SELECT`、`CASE WITHOUT SELECT`、`END SELECT WITHOUT SELECT`、`NOT ALLOWED IN DIRECT MODE` |
| 実行時エラー | 実行中 | `TYPE MISMATCH`、`DIVISION BY ZERO`、`SUBSCRIPT OUT OF RANGE`、`UNDEFINED ARRAY`、`UNDEFINED FUNCTION`、`ARGUMENT COUNT MISMATCH`、`ILLEGAL FUNCTION CALL`、`FILE NOT FOUND`、`OUT OF DATA`、`NETWORK ERROR`（6.1）、`REDIM`、`ARRAY AND VARIABLE NAME CONFLICT`、`STACK OVERFLOW`、`RETURN WITHOUT GOSUB`、`NEXT WITHOUT FOR`（GOTO でループの途中に飛び込んだ場合）、`STEP IS ZERO` |

### 9.2 表示
```
?TYPE MISMATCH IN 12
?SYNTAX ERROR ('=' expected) IN 3
```
- 行番号はソースの行番号（1 始まり。エディタで表示する行番号と同じ）。ダイレクト実行では行番号を付けない。
- 括弧内は補足（あれば）。
- 実行時エラーでは実行を中止する。`ON ERROR`（4.16）を使うと、止めずにエラー処理へ移れる。

---

## 10. 将来の拡張（初版では実装しない）
設計で受け口を用意しておく（[DESIGN.md](DESIGN.md) 9）。
- FUNCTION のデフォルト引数（`FUNCTION F(A, B=10)`）・可変長引数（`FUNCTION F(A, ...REST)`）
- 配列の引数渡し・配列を返す関数
- `DO ... LOOP`
- `RESUME`（エラー処理から、エラーが起きた文に戻ってやり直す）、`ON 式 GOTO / GOSUB`
- 実数型

---

## 付録 A. 予約語
```
AND CASE CONTINUE DATA DICT DIM ELSE ELSIF END ENDIF ERASE EXIT FOR FUNCTION GLOBAL GOSUB GOTO
IF INPUT LET NEXT NOT ON OR PRINT READ REM RESTORE RETURN SELECT STEP THEN TO WEND WHILE
```
（`EXIT` はダイレクト実行の終了命令で、プログラム中では構文エラー。`REM` はコメント。命令拡張で登録した名前も予約語と同じ扱いになる）

## 付録 B. 文法（EBNF）
```ebnf
program     = { line } ;
line        = [ label ] [ statements ] [ comment ] NEWLINE ;
label       = "*" IDENT ;
statements  = statement { ":" statement } ;

statement   = assign | print | input | if | for | next | while | wend
            | exit_loop | continue | select | on_error | goto | gosub | return | end | dim | global
            | data | read | restore | dict | erase
            | function_def | end_function | call_stmt | command ;

assign      = [ "LET" ] lvalue "=" expr ;
lvalue      = IDENT [ "(" expr [ "," expr ] ")" ] ;
print       = ( "PRINT" | "?" ) [ expr { ( ";" | "," ) [ expr ] } ] ;
input       = "INPUT" [ STRING ";" ] lvalue ;

if          = "IF" expr [ "THEN" ]                    (* 文末で終わる → ブロック *)
            | "IF" expr "THEN" statements [ "ELSE" statements ] ;   (* 1 行 IF *)
elsif       = "ELSIF" expr [ "THEN" ] ;
else        = "ELSE" ;
endif       = "ENDIF" | "END" "IF" ;

for         = "FOR" IDENT "=" expr "TO" expr [ "STEP" expr ] ;
next        = "NEXT" [ IDENT ] ;
while       = "WHILE" expr ;
wend        = "WEND" ;
exit_loop   = "EXIT" ( "FOR" | "WHILE" ) ;
continue    = "CONTINUE" [ "FOR" | "WHILE" ] ;
select      = "SELECT" "CASE" expr { case } [ "CASE" "ELSE" statements ] "END" "SELECT" ;
case        = "CASE" case_item { "," case_item } statements ;
case_item   = expr [ "TO" expr ] | "IS" ( "=" | "<>" | "<" | "<=" | ">" | ">=" ) expr ;
on_error    = "ON" "ERROR" ( "GOTO" ( label_ref | "0" ) | "GOSUB" label_ref ) ;
label_ref   = [ "*" ] IDENT ;
goto        = "GOTO" [ "*" ] IDENT ;
gosub       = "GOSUB" [ "*" ] IDENT ;
return      = "RETURN" [ expr ] ;
end         = "END" ;
dim         = "DIM" IDENT "(" expr [ "," expr ] ")" { "," IDENT "(" expr [ "," expr ] ")" } ;
global      = "GLOBAL" IDENT { "," IDENT } ;
data        = "DATA" literal { "," literal } ;
literal     = [ "-" | "+" ] INT | STRING ;
read        = "READ" lvalue { "," lvalue } ;
restore     = "RESTORE" [ [ "*" ] IDENT ] ;
dict        = "DICT" IDENT { "," IDENT } ;
erase       = "ERASE" erase_target { "," erase_target } ;
erase_target= IDENT [ "(" expr ")" ] ;
function_def= "FUNCTION" IDENT "(" [ param { "," param } ] ")" ;
param       = IDENT ;                                 (* 将来: [ "=" expr ] / "..." *)
end_function= "END" "FUNCTION" ;
call_stmt   = IDENT "(" [ expr { "," expr } ] ")" ;
command     = COMMAND_NAME [ expr { "," expr } ] ;

expr        = or_expr ;
or_expr     = and_expr { "OR" and_expr } ;
and_expr    = not_expr { "AND" not_expr } ;
not_expr    = "NOT" not_expr | comparison ;
comparison  = additive { ( "=" | "<>" | "<" | "<=" | ">" | ">=" ) additive } ;
additive    = term { ( "+" | "-" ) term } ;
term        = unary { ( "*" | "/" | "%" ) unary } ;
unary       = ( "-" | "+" ) unary | primary ;
primary     = INT | STRING | IDENT [ "(" [ expr { "," expr } ] ")" ] | "(" expr ")" ;
comment     = ( "REM" | "'" ) { ANY } ;
```
- ブロック構文（IF / FOR / WHILE / SELECT / FUNCTION）の対応は、解析器が行をまたいで確認する。
