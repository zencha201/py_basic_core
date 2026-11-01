"""BASIC language behaviour (BASIC.md)."""

import pytest
from helpers import error_of, run

from py_basic_core import BasicRuntimeError, BasicSyntaxError


def test_print_and_expressions():
    assert run("PRINT 1+2") == "3\n"
    assert run('PRINT "A=";10;"!"') == "A=10!\n"
    assert run('PRINT "X";') == "X"
    assert run("PRINT 1,2") == "1       2\n"
    assert run("PRINT") == "\n"
    assert run("? 2*3+1") == "7\n"
    assert run("PRINT -7/2, -7%2") == "-3      -1\n"
    assert run("PRINT 7/-2;7%-2") == "-3" + "1\n"
    assert run('PRINT "AB"+"C"') == "ABC\n"
    assert run('PRINT "A""B"') == 'A"B\n'
    assert run("PRINT (1+2)*3") == "9\n"


def test_comparison_and_logic():
    assert run("PRINT 1<2;2<1;1=1;1<>1;2>=2;3<=2") == "101010\n"
    assert run('PRINT "A"<"B";"B"="B"') == "11\n"
    assert run("PRINT 1 AND 2;0 OR 0;NOT 0;NOT 5") == "1010\n"
    # AND / OR short-circuit: the division by zero is not evaluated
    assert run("PRINT 0 AND 1/0;1 OR 1/0") == "01\n"


def test_variables_are_case_insensitive_and_typed():
    assert run("player_hp=5:PRINT PLAYER_HP") == "5\n"
    assert run('A=1:A$="S":PRINT A;A$') == "1S\n"
    assert run('PRINT X;"[";X$;"]"') == "0[]\n"
    assert isinstance(error_of('A="X"'), BasicRuntimeError)
    assert error_of('PRINT 1+"A"').name == "TYPE MISMATCH"
    assert error_of("PRINT 1/0").name == "DIVISION BY ZERO"


def test_statements_joined_with_colon_and_comments():
    assert run("A=1:PRINT A:A=A+1:PRINT A") == "1\n2\n"
    assert run("REM nothing\nPRINT 1 ' comment\n' line") == "1\n"


def test_arrays():
    assert run("DIM A(10)\nA(0)=100:A(10)=5\nPRINT A(0);A(10);A(3)") == "10050\n"
    assert run("DIM MAP(32,32)\nMAP(32,1)=7\nPRINT MAP(32,1)") == "7\n"
    assert run('DIM N$(2)\nN$(1)="X"\nPRINT N$(1)') == "X\n"
    assert run("DIM A(1),B(2)\nB(2)=3:PRINT B(2)") == "3\n"
    assert error_of("DIM A(10)\nA(11)=1").name == "SUBSCRIPT OUT OF RANGE"
    assert error_of("DIM A(2)\nDIM A(3)").name == "REDIM"
    assert error_of("A(1)=2").name == "UNDEFINED ARRAY"
    assert error_of("DIM A(1,2,3)").name == "SYNTAX ERROR"


def test_labels_goto_gosub():
    src = """
I=0
*START
I=I+1
IF I<3 THEN GOTO START
PRINT I
GOSUB SUB1
GOSUB *SUB1
END
*SUB1
PRINT "SUB"
RETURN
"""
    assert run(src) == "3\nSUB\nSUB\n"
    assert error_of("GOTO NOWHERE").name == "UNDEFINED LABEL"
    assert error_of("*A\n*A").name == "DUPLICATE LABEL"
    assert error_of("RETURN").name == "RETURN WITHOUT GOSUB"


def test_if_forms():
    block = """
A={}
IF A=1 THEN
    PRINT "ONE"
ELSIF A=2 THEN
    PRINT "TWO"
ELSIF A=3
    PRINT "THREE"
ELSE
    PRINT "OTHER"
ENDIF
"""
    assert [run(block.format(n)) for n in (1, 2, 3, 4)] == ["ONE\n", "TWO\n", "THREE\n", "OTHER\n"]
    assert run('A=1\nIF A=1\n  PRINT "A"\nENDIF') == "A\n"
    assert run('A=1\nIF A=1 THEN\n  PRINT "A"\nEND IF') == "A\n"
    assert run('A=1:IF A=1 THEN PRINT "A"') == "A\n"
    assert run('A=2:IF A=1 THEN PRINT "A" ELSE PRINT "B"') == "B\n"
    assert run('A=1:IF A=1 THEN PRINT "A":PRINT "C" ELSE PRINT "B":PRINT "D"') == "A\nC\n"
    assert run("IF 1 THEN IF 0 THEN PRINT 1 ELSE PRINT 2") == "2\n"
    assert run('IF 0 THEN PRINT "X"\nPRINT "Y"') == "Y\n"
    assert error_of("IF 1\nPRINT 1").name == "IF WITHOUT ENDIF"
    assert error_of("ENDIF").name == "ENDIF WITHOUT IF"
    assert error_of("IF 1 PRINT 1").name == "SYNTAX ERROR"


def test_for_next():
    assert run("FOR I=1 TO 3\nPRINT I;\nNEXT") == "123"
    assert run("FOR I=1 TO 3:PRINT I;:NEXT I") == "123"
    assert run("FOR I=10 TO 0 STEP -5\nPRINT I;\nNEXT INDEX") == "1050"
    assert run("FOR I=5 TO 1\nPRINT I\nNEXT\nPRINT I") == "5\n"
    assert run("FOR I=1 TO 2:NEXT:PRINT I") == "3\n"
    assert run("FOR I=1 TO 2\nFOR J=1 TO 2\nPRINT I*10+J;\" \";\nNEXT\nNEXT") == "11 12 21 22 "
    assert run("FOR I=1 TO 10\nIF I=3 THEN GOTO DONE\nNEXT\n*DONE\nPRINT I") == "3\n"
    assert error_of("FOR I=1 TO 2 STEP 0\nNEXT").name == "STEP IS ZERO"
    assert error_of("FOR I=1 TO 2").name == "FOR WITHOUT NEXT"
    assert error_of("NEXT").name == "NEXT WITHOUT FOR"


def test_while_wend():
    assert run("A=0\nWHILE A<3\nA=A+1\nWEND\nPRINT A") == "3\n"
    assert run("WHILE 0:PRINT 1:WEND:PRINT 2") == "2\n"
    assert error_of("WHILE 1").name == "WHILE WITHOUT WEND"


def test_end_stops_the_program():
    assert run('PRINT 1\nEND\nPRINT 2') == "1\n"


def test_input():
    assert run("INPUT NAME$\nPRINT NAME$", ["DAISUKE"]) == "? DAISUKE\nDAISUKE\n"
    assert run('INPUT "AGE";A\nPRINT A+1', ["41"]) == "AGE? 41\n42\n"
    assert run("INPUT A\nPRINT A", ["X", "-3"]) == "? X\n?REDO\n? -3\n-3\n"
    assert run("DIM A(2)\nINPUT A(1)\nPRINT A(1)", ["5"]) == "? 5\n5\n"
    assert run("INPUT A\nPRINT A", [""]) == "? \n0\n"


def test_user_functions_forward_reference_and_recursion():
    src = """
PRINT ADD(1,2)
PRINT FACT(10)
PRINT GREET$("X")
FUNCTION ADD(A,B)
    RETURN A+B
END FUNCTION
FUNCTION FACT(N)
    IF N<=1 THEN RETURN 1
    RETURN N*FACT(N-1)
END FUNCTION
FUNCTION GREET$(NAME$)
    RETURN "HELLO "+NAME$
END FUNCTION
"""
    assert run(src) == "3\n3628800\nHELLO X\n"


def test_function_definition_is_skipped_when_reached():
    assert run("PRINT 1\nFUNCTION F()\nPRINT 99\nEND FUNCTION\nPRINT 2") == "1\n2\n"
    assert run("PRINT F()\nFUNCTION F()\nPRINT 99\nEND FUNCTION") == "99\n0\n"


def test_function_scope_and_global():
    src = """
SCORE=0
VALUE=100
ADD_SCORE(5)
ADD_SCORE(7)
TEST()
PRINT SCORE;" ";VALUE
FUNCTION ADD_SCORE(V)
    GLOBAL SCORE
    SCORE=SCORE+V
END FUNCTION
FUNCTION TEST()
    VALUE=200
    RETURN VALUE
END FUNCTION
"""
    assert run(src) == "12 100\n"
    src = """
HP=1:MP=2
SHOW()
FUNCTION SHOW()
    GLOBAL HP,MP
    PRINT HP;MP;X
END FUNCTION
"""
    assert run(src) == "120\n"


def test_local_variables_per_call():
    src = """
PRINT F(3)
FUNCTION F(N)
    A=N
    IF N>0 THEN B=F(N-1)
    RETURN A
END FUNCTION
"""
    assert run(src) == "3\n"


def test_global_array_and_local_array():
    src = """
DIM G(3)
SETG()
PRINT G(1)
FUNCTION SETG()
    GLOBAL G
    G(1)=42
    DIM L(2)
    L(0)=1
END FUNCTION
"""
    assert run(src) == "42\n"
    # without GLOBAL the array is not visible inside the function
    assert error_of("DIM G(3)\nX=F()\nFUNCTION F()\nRETURN G(1)\nEND FUNCTION").name == "UNDEFINED FUNCTION"


def test_name_resolution_array_before_function():
    src = """
DIM ABS(2)
ABS(1)=9
PRINT ABS(1)
"""
    assert run(src) == "9\n"


def test_gosub_inside_function():
    src = """
PRINT F()
FUNCTION F()
    GOSUB INNER
    RETURN 5
*INNER
    PRINT "IN"
    RETURN
END FUNCTION
"""
    assert run(src) == "IN\n5\n"


def test_function_errors():
    assert error_of("PRINT ADD(1)\nFUNCTION ADD(A,B)\nRETURN A+B\nEND FUNCTION").name == \
        "ARGUMENT COUNT MISMATCH"
    assert error_of("PRINT F(\"X\")\nFUNCTION F(A)\nRETURN A\nEND FUNCTION").name == "TYPE MISMATCH"
    assert error_of("PRINT NOPE(1)").name == "UNDEFINED FUNCTION"
    assert error_of("GLOBAL A").name == "SYNTAX ERROR"
    assert error_of("FUNCTION F()\nEND FUNCTION\nFUNCTION F()\nEND FUNCTION").name == "DUPLICATE FUNCTION"
    assert error_of("FUNCTION F()").name == "FUNCTION WITHOUT END FUNCTION"
    assert error_of("IF 1 THEN\nFUNCTION F()\nEND FUNCTION\nENDIF").name == "SYNTAX ERROR"
    assert error_of("X=F()\nFUNCTION F()\nX=F()\nEND FUNCTION").name == "STACK OVERFLOW"


def test_end_inside_function_ends_program():
    assert run("X=F()\nPRINT 2\nFUNCTION F()\nPRINT 1\nEND\nEND FUNCTION") == "1\n"


def test_error_line_numbers():
    e = error_of("PRINT 1\n\nPRINT 1/0")
    assert e.line == 3 and e.message() == "?DIVISION BY ZERO IN 3"
    e = error_of("PRINT 1\nPRINT (")
    assert isinstance(e, BasicSyntaxError) and e.line == 2


@pytest.mark.parametrize("src, out", [
    ('PRINT ABS(-3);MIN(3,1,2);MAX(3,1,2);LEN("ABC")', "3133\n"),
    ('PRINT LEFT$("ABCDE",2);RIGHT$("ABCDE",2);MID$("ABCDE",2,3);MID$("ABCDE",4)', "ABDEBCDDE\n"),
    ('PRINT STR$(-5)+"!";VAL(" 12AB");VAL("X");VAL("-7")', "-5!120-7\n"),
    ('PRINT CHR$(65);ASC("A");INSTR("HELLO","LL");INSTR("A","Z")', "A6530\n"),
    ('PRINT LEN("日本語");LEFT$("ABC",10)', "3ABC\n"),
])
def test_standard_functions(src, out):
    assert run(src) == out


def test_rnd_range():
    assert run("FOR I=1 TO 50\nIF RND(3)<0 OR RND(3)>2 THEN PRINT \"BAD\"\nNEXT") == ""
    assert error_of("PRINT RND(0)").name == "ILLEGAL FUNCTION CALL"


def test_data_read_restore():
    assert run('READ A,B$\nPRINT A;B$\nDATA 1,"X"') == "1X\n"
    src = """
DIM A(2)
FOR I=0 TO 2:READ A(I):NEXT
PRINT A(0);A(1);A(2)
RESTORE
READ X:PRINT X
RESTORE SECOND
READ Y:PRINT Y
END
DATA 1,+2
*SECOND
DATA -3
"""
    assert run(src) == "12-3\n1\n-3\n"
    # DATA anywhere (inside blocks too), read in source order
    assert run('IF 0 THEN\nDATA 1\nENDIF\nREAD A,B\nPRINT A;B\nDATA 2') == "12\n"
    # READ / RESTORE inside a function use the DATA of the main program
    src = "PRINT F()\nFUNCTION F()\nRESTORE L\nREAD A\nRETURN A\nEND FUNCTION\nDATA 5\n*L\nDATA 7"
    assert run(src) == "7\n"


def test_data_errors():
    assert error_of("READ A\nREAD B\nDATA 1").name == "OUT OF DATA"
    assert error_of("READ A$\nDATA 1").name == "TYPE MISMATCH"
    assert error_of('READ A\nDATA "X"').name == "TYPE MISMATCH"
    assert error_of("RESTORE NOPE").name == "UNDEFINED LABEL"
    assert error_of("FUNCTION F()\nDATA 1\nEND FUNCTION").name == "SYNTAX ERROR"
    assert error_of("DATA A").name == "SYNTAX ERROR"
    assert error_of("DATA").name == "SYNTAX ERROR"


def test_dict_basics():
    src = """
DICT HP, JOB$
HP("SLIME")=5
HP(1)=3
HP("1")=HP("1")+1
JOB$("TARO")="WARRIOR"
PRINT HP("SLIME");",";HP(1);",";HP("NONE");",[";JOB$("NONE");"],";JOB$("TARO")
PRINT HASKEY(HP,"SLIME");HASKEY(HP,1);HASKEY(HP,"2");COUNT(HP);COUNT(JOB$)
"""
    assert run(src) == "5,4,0,[],WARRIOR\n11021\n"


def test_dict_keys_in_order_and_erase():
    src = """
DICT D
D("B")=1:D("A")=2:D(10)=3:D("B")=4
FOR I=0 TO COUNT(D)-1
    K$=KEY$(D,I)
    PRINT K$;"=";D(K$);" ";
NEXT
PRINT
ERASE D("A"),D("NONE")
PRINT COUNT(D);KEY$(D,1)
ERASE D
PRINT COUNT(D)
"""
    assert run(src) == "B=4 A=2 10=3 \n210\n0\n"


def test_dict_with_input_read_and_functions():
    assert run('DICT D\nREAD D("X"),D(2)\nPRINT D("X")+D("2")\nDATA 3,4') == "7\n"
    assert run('DICT N$\nINPUT N$("A")\nPRINT N$("A")', ["HI"]) == "? HI\nHI\n"
    src = """
DICT G
FILL()
PRINT COUNT(G);G("K")
FUNCTION FILL()
    GLOBAL G
    G("K")=7
    DICT L
    L(1)=1
END FUNCTION
"""
    assert run(src) == "17\n"


def test_dict_errors():
    assert error_of('DICT D\nD("A")="S"').name == "TYPE MISMATCH"
    assert error_of("DICT D\nD(1,2)=3").name == "SUBSCRIPT OUT OF RANGE"
    assert error_of("DICT D\nDICT D").name == "REDIM"
    assert error_of("DIM D(3)\nDICT D").name == "REDIM"
    assert error_of("D=1\nDICT D").name == "ARRAY AND VARIABLE NAME CONFLICT"
    assert error_of('DIM A(3)\nA("X")=1').name == "TYPE MISMATCH"
    assert error_of("DIM A(3)\nERASE A").name == "TYPE MISMATCH"
    assert error_of("ERASE NONE").name == "UNDEFINED ARRAY"
    assert error_of("DICT D\nPRINT KEY$(D,0)").name == "SUBSCRIPT OUT OF RANGE"
    assert error_of("A=1\nPRINT COUNT(A)").name == "TYPE MISMATCH"
    # a DICT itself is not a value
    assert error_of("DICT D\nPRINT D").name == "TYPE MISMATCH"
    assert error_of("DICT D\nX=D").name == "TYPE MISMATCH"
    assert error_of("DICT D\nPRINT D+1").name == "TYPE MISMATCH"
    assert error_of("DICT D\nIF D=1 THEN PRINT 1").name == "TYPE MISMATCH"
    assert error_of("DICT D\nERASE D(1,2)").name == "SYNTAX ERROR"


def test_exit_for_and_exit_while():
    assert run("FOR I=1 TO 10\nIF I=4 THEN EXIT FOR\nPRINT I;\nNEXT\nPRINT \"/\";I") == "123/4\n"
    assert run("I=0\nWHILE 1\nI=I+1\nIF I>3 THEN EXIT WHILE\nWEND\nPRINT I") == "4\n"
    # one line, and EXIT inside IF blocks
    assert run("FOR I=1 TO 9:IF I=3 THEN EXIT FOR\nNEXT:PRINT I") == "3\n"
    src = """
FOR I=1 TO 3
    FOR J=1 TO 3
        IF J=2 THEN
            EXIT FOR
        ENDIF
        PRINT I;J;" ";
    NEXT
NEXT
PRINT
"""
    assert run(src) == "11 21 31 \n"


def test_exit_leaves_inner_loops():
    # EXIT WHILE from inside a FOR also leaves the FOR; running it again works
    src = """
N=0
FOR K=1 TO 2
    WHILE 1
        FOR I=1 TO 5
            N=N+1
            IF I=2 THEN EXIT WHILE
        NEXT
    WEND
NEXT
PRINT N
"""
    assert run(src) == "4\n"
    # EXIT FOR inside a WHILE inside a FOR leaves both
    assert run("FOR I=1 TO 5\nWHILE 1\nEXIT FOR\nWEND\nNEXT\nPRINT I") == "1\n"
    # inside a function
    assert run("PRINT F()\nFUNCTION F()\nFOR I=1 TO 9\nIF I*I>20 THEN EXIT FOR\nNEXT\nRETURN I\nEND FUNCTION") == "5\n"


def test_exit_loop_errors():
    assert error_of("EXIT FOR").name == "EXIT FOR WITHOUT FOR"
    assert error_of("FOR I=1 TO 2\nEXIT WHILE\nNEXT").name == "EXIT WHILE WITHOUT WHILE"
    assert error_of("EXIT").name == "SYNTAX ERROR"      # plain EXIT is for direct mode
