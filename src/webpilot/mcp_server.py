import sys
import json
import uuid
import time
import logging
from logging import StreamHandler
from typing import Any, Dict

from browser import start_browser, stop_browser
import tools as Tools

# ---- Minimal JSON-RPC/STDIO MCP-like server ----
# Supported methods:
#  - initialize
#  - tools/list
#  - tools/call {name:str, arguments:dict}

SERVER_NAME = "tw3-mcp"
SERVER_VERSION = "0.1.0"

# We keep a single Playwright browser/page per server process.
P = None
BROWSER = None
PAGE = None

# ---- Logging to STDERR in JSON (to not break STDIO protocol) ----
class JsonStderrFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if hasattr(record, "meta") and isinstance(record.meta, dict):
            base.update(record.meta)
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)

logger = logging.getLogger(SERVER_NAME)
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = StreamHandler(sys.stderr)
    h.setFormatter(JsonStderrFormatter())
    logger.addHandler(h)

def ensure_browser():
    global P, BROWSER, PAGE
    if PAGE is None:
        P, BROWSER, PAGE = start_browser()
        logger.info("browser_started", extra={"meta": {"stage": "init"}})

def shutdown_browser():
    global P, BROWSER, PAGE
    try:
        stop_browser(P, BROWSER)
    except Exception:
        pass
    finally:
        P = None
        BROWSER = None
        PAGE = None
        logger.info("browser_stopped", extra={"meta": {"stage": "shutdown"}})

def ok(tool: str, url: str | None, data: Dict[str, Any] | None = None, meta: Dict[str, Any] | None = None):
    return {"ok": True, "tool": tool, "url": url, "data": data or {}, "meta": meta or {}}

def fail(tool: str, url: str | None, message: str, code: str | None = None, details: Any = None):
    return {"ok": False, "tool": tool, "url": url, "error": {"message": message, "code": code, "details": details}}

def list_tools():
    # Input schemas are intentionally simple; they document expected args.
    return [
        {"name": "navigate", "description": "Go to a URL", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
        {"name": "screenshot", "description": "Take a screenshot", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "full": {"type": "boolean"}}, "required": []}},
        {"name": "extract_links", "description": "Extract links on page (optional text filter)", "inputSchema": {"type": "object", "properties": {"contains": {"type": "string"}}, "required": []}},
        {"name": "fill", "description": "Fill a form element", "inputSchema": {"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}}, "required": ["selector", "text"]}},
        {"name": "click", "description": "Click an element", "inputSchema": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}},
        {"name": "get_html", "description": "Get full HTML (post-JS)", "inputSchema": {"type": "object", "properties": {"save_path": {"type": "string"}}, "required": []}},
    ]

def handle_call(name: str, args: Dict[str, Any] | None):
    ensure_browser()
    args = args or {}
    rid = str(uuid.uuid4())
    t0 = time.time()

    try:
        if name == "navigate":
            res = Tools.navigate(PAGE, args["url"])
            outcome = "ok" if res.get("ok") else "fail"
            logger.info("navigate", extra={"meta": {"rid": rid, "url": args.get("url"), "outcome": outcome}})
            return res

        elif name == "screenshot":
            path = args.get("path", f"snap_{int(time.time()*1000)}.png")
            full = bool(args.get("full", False))
            res = Tools.screenshot(PAGE, path=path, full=full)
            logger.info("screenshot", extra={"meta": {"rid": rid, "url": getattr(PAGE, 'url', None), "path": path, "full": full, "outcome": "ok" if res.get("ok") else "fail"}})
            return res

        elif name == "extract_links":
            res = Tools.extract_links(PAGE, args.get("contains"))
            logger.info("extract_links", extra={"meta": {"rid": rid, "count": res.get("count"), "url": getattr(PAGE, 'url', None), "outcome": "ok" if res.get("ok") else "fail"}})
            return res

        elif name == "fill":
            res = Tools.fill(PAGE, args["selector"], args["text"])
            logger.info("fill", extra={"meta": {"rid": rid, "selector": args.get("selector"), "url": getattr(PAGE, 'url', None), "outcome": "ok" if res.get("ok") else "fail"}})
            return res

        elif name == "click":
            res = Tools.click(PAGE, args["selector"])
            logger.info("click", extra={"meta": {"rid": rid, "selector": args.get("selector"), "url": getattr(PAGE, 'url', None), "outcome": "ok" if res.get("ok") else "fail"}})
            return res

        elif name == "get_html":
            # Tools.get_html currently returns sample; we accept optional save_path to avoid giant payloads
            if "save_path" in args and args["save_path"]:
                # patch: call Tools.get_html then write if needed (Tools currently doesn't support save_path)
                res = Tools.get_html(PAGE)
                if res.get("ok"):
                    content = res.get("sample")  # Tools.get_html returns 'sample' (first 500 chars). We fetch full content again:
                    try:
                        full_html = PAGE.content()
                        with open(args["save_path"], "w", encoding="utf-8") as f:
                            f.write(full_html)
                        payload = {"length": len(full_html), "saved_to": args["save_path"]}
                        out = ok("get_html", getattr(PAGE, 'url', None), payload)
                        logger.info("get_html", extra={"meta": {"rid": rid, "url": getattr(PAGE, 'url', None), "saved_to": args["save_path"], "outcome": "ok"}})
                        return out
                    except Exception as w:
                        out = fail("get_html", getattr(PAGE, 'url', None), "unable to save HTML", code="E_SAVE", details=str(w))
                        logger.error("get_html", extra={"meta": {"rid": rid, "url": getattr(PAGE, 'url', None), "outcome": "fail", "code": "E_SAVE", "details": str(w)}})
                        return out
                else:
                    logger.error("get_html", extra={"meta": {"rid": rid, "url": getattr(PAGE, 'url', None), "outcome": "fail"}})
                    return res
            else:
                res = Tools.get_html(PAGE)
                logger.info("get_html", extra={"meta": {"rid": rid, "url": getattr(PAGE, 'url', None), "outcome": "ok" if res.get("ok") else "fail"}})
                return res

        else:
            logger.error("unknown_tool", extra={"meta": {"rid": rid, "name": name}})
            return fail(name, getattr(PAGE, 'url', None), f"unknown tool '{name}'", code="E_TOOL")

    except Exception as e:
        logger.exception("tools_call_exception", extra={"meta": {"rid": rid, "name": name}})
        return fail(name, getattr(PAGE, 'url', None), "exception during tool call", code="E_SERVER", details=str(e))
    finally:
        dur = int((time.time() - t0) * 1000)
        logger.info("call_duration", extra={"meta": {"rid": rid, "name": name, "duration_ms": dur}})

def handle_message(msg: Dict[str, Any]):
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params", {})

    if method == "initialize":
        ensure_browser()
        result = {"serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}}
        return {"id": mid, "result": result}

    if method == "tools/list":
        return {"id": mid, "result": {"tools": list_tools()}}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        result = handle_call(name, arguments)
        return {"id": mid, "result": result}

    if method == "shutdown":
        shutdown_browser()
        return {"id": mid, "result": {"ok": True}}

    return {"id": mid, "error": {"code": "E_METHOD", "message": f"unknown method '{method}'"}}

def main():
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as e:
                sys.stdout.write(json.dumps({"error": {"code": "E_JSON", "message": str(e)}}) + "\n")
                sys.stdout.flush()
                continue
            resp = handle_message(msg)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    finally:
        shutdown_browser()

if __name__ == "__main__":
    main()
