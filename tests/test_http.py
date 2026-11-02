"""HTTP command (BASIC.md 6.1), against a local server."""

import http.server
import json
import threading
import time
import urllib.parse

import pytest

from py_basic_core import BufferHost, Runtime, RunState, install_http, install_standard
from py_basic_core.stdlib.http import flatten, nest


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type="application/json"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def echo(self):
        url = urllib.parse.urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8")
        if url.path == "/slow":
            time.sleep(1)
        if url.path == "/text":
            self.reply(200, "plain text", "text/plain")
        elif url.path == "/missing":
            self.reply(404, '{"error":"not found"}')
        elif url.path == "/list":
            self.reply(200, '[{"id":5,"ok":true},{"id":7,"ok":false,"note":null}]')
        else:
            self.reply(200, json.dumps({
                "method": self.command, "query": urllib.parse.parse_qs(url.query),
                "type": self.headers.get("Content-Type", ""), "token": self.headers.get("X-Token", ""),
                "body": body, "pi": 3.14, "user": {"name": "タロウ", "level": 3}}))

    do_GET = do_POST = do_PUT = do_DELETE = echo


@pytest.fixture(scope="module")
def base():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % server.server_address[1]
    server.shutdown()


def run(source, timeout=5):
    host = BufferHost()
    rt = Runtime(host)
    install_standard(rt)
    install_http(rt, timeout=timeout)
    rt.load(source)
    for _ in range(1000):
        state = rt.run(10000)
        if state not in (RunState.RUNNING, RunState.WAITING_FRAMES):
            break
        time.sleep(0.01)                    # a frame
    return rt, host.output


def test_get_with_query_and_json_reply(base):
    rt, out = run('''
DICT Q$, R$
Q$("name") = "TARO"
Q$("page") = "2"
HTTP "GET", "%s/echo", Q$, R$
PRINT HTTPSTATUS()
PRINT R$("method"); " "; R$("query.name.0"); " "; R$("query.page.#")
PRINT R$("user.name"); " "; R$("user.level"); " "; R$("pi")
''' % base)
    assert rt.state == RunState.FINISHED, rt.error
    assert out.split("\n")[:3] == ["200", "GET TARO 1", "タロウ 3 3.14"]


def test_post_json_from_int_and_string_dicts(base):
    rt, out = run('''
DICT D, R$, H$
D("score") = 90
D("pos.x") = 1
H$("X-Token") = "ABC"
HTTP "post", "%s/echo", D, R$, H$
PRINT R$("method"); " "; R$("type"); " "; R$("token")
PRINT R$("body")
''' % base)
    lines = out.split("\n")
    assert lines[0] == "POST application/json; charset=utf-8 ABC"
    assert json.loads(lines[1]) == {"score": 90, "pos": {"x": 1}}


def test_post_form(base):
    rt, out = run('''
DICT D$, R$, H$
D$("name") = "TARO YAMADA"
D$("memo") = "a&b"
H$("Content-Type") = "application/x-www-form-urlencoded"
HTTP "POST", "%s/echo", D$, R$, H$
PRINT R$("body")
''' % base)
    assert out.split("\n")[0] == "name=TARO+YAMADA&memo=a%26b"


def test_array_reply_status_and_body(base):
    rt, out = run('''
DICT R$
HTTP "GET", "%s/list", "", R$
FOR I = 0 TO COUNT(R$) - 1
    PRINT KEY$(R$, I); "="; R$(KEY$(R$, I))
NEXT
HTTP "GET", "%s/missing", "", R$
PRINT HTTPSTATUS(); " "; R$("error")
HTTP "GET", "%s/text", "", R$
PRINT HTTPSTATUS(); " "; COUNT(R$); " "; HTTPBODY$()
''' % (base, base, base))
    assert out.split("\n")[:9] == ["0.id=5", "0.ok=1", "1.id=7", "1.ok=0", "1.note=", "#=2",
                                   "404 not found", "200 0 plain text", ""]


def test_network_errors_can_be_caught(base):
    rt, out = run('''
ON ERROR GOTO *E
DICT R$
R$("OLD") = "X"
HTTP "GET", "%s/slow", "", R$
PRINT "NO"
END
*E
PRINT ERR$(); " "; ERL(); " "; COUNT(R$); " "; HTTPSTATUS()
''' % base, timeout=0.2)
    assert rt.state == RunState.FINISHED
    assert out.startswith("NETWORK ERROR 5 0 0")


def test_argument_errors():
    for source, message in [
        ('DICT R$\nHTTP "GET", "", "", R$', "URL must start with http"),
        ('DICT R$\nHTTP "GET", "ftp://x", "", R$', "URL must start with http"),
        ('DICT R\nHTTP "GET", "http://x", "", R', "reply must be a STRING DICT"),
        ('DICT R$\nHTTP "G T", "http://x", "", R$', "method G T"),
        ('DICT R$\nHTTP "GET", "http://x", 1, R$', "TYPE MISMATCH"),
    ]:
        rt, _ = run(source)
        assert rt.state == RunState.ERROR and message in rt.error.message(), (source, rt.error)


def test_nest_and_flatten():
    assert nest([("a.b", 1), ("a.c", "x"), ("d", 2)]) == {"a": {"b": 1, "c": "x"}, "d": 2}
    with pytest.raises(Exception):
        nest([("a", 1), ("a.b", 2)])
    assert flatten({"a": [], "b": {}, "c": 2.0, "d": [[1]]}) == [
        ("a.#", "0"), ("c", "2"), ("d.0.0", "1"), ("d.0.#", "1"), ("d.#", "1")]
    assert flatten("text") == [] and flatten(None) == []
