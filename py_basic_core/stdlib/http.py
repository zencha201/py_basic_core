"""HTTP / HTTPS requests: the HTTP command and HTTPSTATUS() / HTTPBODY$() (BASIC.md 6.1).

    DICT REQ$, RES$
    REQ$("name") = "TARO"
    HTTP "POST", URL$, REQ$, RES$
    PRINT HTTPSTATUS(); RES$("user.id")

The request runs in a thread, and the command waits with WaitUntil, so a front
end keeps drawing and can stop the program meanwhile. The data sent comes from
a DICT (the URL query for GET / DELETE / HEAD, a JSON or form body otherwise);
a JSON reply is parsed and stored, flattened, in a STRING DICT.

Not part of install_standard(): an application that lets BASIC programs use
the network calls install_http(runtime).
"""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request

from ..errors import ILLEGAL_FUNCTION_CALL, NETWORK_ERROR, TYPE_MISMATCH, BasicRuntimeError
from ..function import WaitUntil
from ..variable import BasicDict

TIMEOUT = 10                    # seconds
MAX_BYTES = 4 * 1024 * 1024     # largest reply read
QUERY_METHODS = ("GET", "DELETE", "HEAD")
FORM_TYPE = "application/x-www-form-urlencoded"
JSON_TYPE = "application/json"
COUNT_KEY = "#"                 # number of elements of a JSON array: RES$("items.#")


# --- the data sent -----------------------------------------------------------------
def dict_items(d):
    """(key, value) of a DICT; values of an INT DICT stay numbers."""
    return list(d.data.items())


def nest(items):
    """{"a.b": 1} -> {"a": {"b": 1}} (a "." in a key makes a nested object)."""
    root = {}
    for key, value in items:
        parts = key.split(".")
        node = root
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail="key conflict: " + key)
            node = child
        if isinstance(node.get(parts[-1]), dict):
            raise BasicRuntimeError(ILLEGAL_FUNCTION_CALL, detail="key conflict: " + key)
        node[parts[-1]] = value
    return root


def form_text(items):
    return urllib.parse.urlencode([(key, str(value)) for key, value in items])


def build_request(method, url, data, headers):
    """A urllib Request for the HTTP command's arguments (data: a DICT or None)."""
    headers = dict(headers)
    lower = {k.lower(): k for k in headers}
    items = dict_items(data) if data is not None else []
    body = None
    if method in QUERY_METHODS:
        if items:
            url += ("&" if "?" in url else "?") + form_text(items)
    else:
        content_type = headers.get(lower.get("content-type", ""), "")
        if FORM_TYPE in content_type.lower():
            body = form_text(items).encode("utf-8")
        else:
            body = json.dumps(nest(items), ensure_ascii=False).encode("utf-8")
            if "content-type" not in lower:
                headers["Content-Type"] = JSON_TYPE + "; charset=utf-8"
    if "accept" not in lower:
        headers["Accept"] = JSON_TYPE + ", */*"
    return urllib.request.Request(url, data=body, headers=headers, method=method)


# --- the reply ---------------------------------------------------------------------
def flat_value(value):
    if value is None:
        return ""
    if value is True or value is False:
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return str(value)


def flatten(value, prefix=""):
    """Parsed JSON -> [(key, string)]: {"a": [{"b": 1}]} -> a.0.b = "1", a.# = "1"."""
    out = []
    if isinstance(value, dict):
        for key, child in value.items():
            out += flatten(child, prefix + str(key) + ".")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            out += flatten(child, prefix + str(i) + ".")
        out.append((prefix + COUNT_KEY, str(len(value))))
    elif prefix:
        out.append((prefix[:-1], flat_value(value)))
    return out


def parse_json(text):
    """The parsed JSON object or array, or None when the text is not one."""
    if not text.lstrip()[:1] in ("{", "["):
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


class Request:
    """One request running in a thread. ``done`` turns True when it has finished."""

    def __init__(self, request, timeout):
        self.request = request
        self.timeout = timeout
        self.done = False
        self.status = 0
        self.body = ""
        self.error = None           # text of a network error

    def start(self):
        try:
            threading.Thread(target=self._run, daemon=True).start()
        except RuntimeError as e:   # no threads (e.g. in a web browser)
            self.error = "not supported here: %s" % e
            self.done = True

    def _run(self):
        try:
            try:
                reply = urllib.request.urlopen(self.request, timeout=self.timeout)
            except urllib.error.HTTPError as e:     # 4xx / 5xx: a reply, not an error
                reply = e
            with reply:
                data = reply.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("reply larger than %d bytes" % MAX_BYTES)
                charset = reply.headers.get_content_charset() or "utf-8"
                self.status = reply.status
                self.body = data.decode(charset, errors="replace")
        except urllib.error.URLError as e:
            self.error = str(e.reason)
        except Exception as e:      # timeouts, bad addresses, broken connections, ...
            self.error = str(e) or type(e).__name__
        finally:
            self.done = True


# --- BASIC ---------------------------------------------------------------------------
def install_http(runtime, timeout=TIMEOUT):
    last = {"status": 0, "body": ""}

    def dict_arg(ctx, value, what, string_only=False):
        """A DICT argument, or None for "" (no data)."""
        if value == "":
            return None
        d = ctx.expect_dict(value)
        if string_only and not d.name.endswith("$"):
            raise ctx.error(TYPE_MISMATCH, what + " must be a STRING DICT")
        return d

    def http_command(ctx, args):
        """HTTP method$, url$, data, reply$[, headers$]"""
        method = ctx.expect_str(args[0]).strip().upper()
        url = ctx.expect_str(args[1]).strip()
        data = dict_arg(ctx, args[2], "data")
        reply = ctx.expect_dict(args[3])
        if not reply.name.endswith("$"):
            raise ctx.error(TYPE_MISMATCH, "reply must be a STRING DICT")
        header_dict = dict_arg(ctx, args[4], "headers", True) if len(args) > 4 else None
        if not method.isalpha():
            raise ctx.error(ILLEGAL_FUNCTION_CALL, "method " + method)
        if not url.lower().startswith(("http://", "https://")):
            raise ctx.error(ILLEGAL_FUNCTION_CALL, "URL must start with http:// or https://")
        headers = dict(dict_items(header_dict)) if header_dict is not None else {}
        try:
            request = Request(build_request(method, url, data, headers), timeout)
        except ValueError as e:     # a URL urllib cannot use
            raise ctx.error(ILLEGAL_FUNCTION_CALL, str(e))
        request.start()

        def finish():
            last["status"], last["body"] = request.status, request.body
            reply.clear()
            if request.error is not None:
                raise BasicRuntimeError(NETWORK_ERROR, detail=request.error)
            for key, value in flatten(parse_json(request.body)):
                reply.set([key], value)

        return WaitUntil(lambda: request.done, finish)

    runtime.register_command("HTTP", http_command, 4, 5)
    runtime.register_function("HTTPSTATUS", lambda ctx, args: last["status"], 0, 0)
    runtime.register_function("HTTPBODY$", lambda ctx, args: last["body"], 0, 0)
