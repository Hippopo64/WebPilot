
"""
Tiny demo client that exercises the required scenario against the STDIO server.

Usage:
  # Terminal 1
  python mcp_server.py

  # Terminal 2
  python demo_mcp_client.py
"""
import json
import subprocess
import time
import sys
from urllib.parse import urlparse

def send(proc, obj):
    proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
    proc.stdin.flush()

def recv(proc):
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("server closed")
    return json.loads(line.decode("utf-8"))

def first_external(links, current_host):
    for l in links:
        try:
            host = urlparse(l["href"]).netloc
            if host and host != current_host:
                return l["href"]
        except Exception:
            pass
    return None

def main():
    server = subprocess.Popen([sys.executable, "mcp_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # 1) initialize
        send(server, {"id": 1, "method": "initialize"})
        print("INIT:", recv(server))

        # 2) list tools
        send(server, {"id": 2, "method": "tools/list"})
        print("TOOLS:", recv(server))

        # 3) navigate example.com
        send(server, {"id": 3, "method": "tools/call", "params": {"name": "navigate", "arguments": {"url": "https://example.com"}}})
        nav = recv(server); print("NAV:", nav)
        assert nav["result"]["ok"], "navigate failed"
        current_url = nav["result"]["url"]
        host = urlparse(current_url).netloc

        # 4) screenshot viewport
        send(server, {"id": 4, "method": "tools/call", "params": {"name": "screenshot", "arguments": {"path": "example_viewport.png", "full": False}}})
        print("SHOT1:", recv(server))

        # 5) extract links
        send(server, {"id": 5, "method": "tools/call", "params": {"name": "extract_links"}})
        links = recv(server)
        print("LINKS:", links)
        links_payload = links["result"]
        assert links_payload.get("ok"), "extract_links failed"
        ext = first_external(links_payload.get("links", []), host)

        if not ext:
            print("No external link found on example.com; exiting.")
            send(server, {"id": 99, "method": "shutdown"})
            print("SHUT:", recv(server))
            return

        # 6) navigate to first external link
        send(server, {"id": 6, "method": "tools/call", "params": {"name": "navigate", "arguments": {"url": ext}}})
        print("NAV-EXT:", recv(server))

        # 7) full page screenshot
        send(server, {"id": 7, "method": "tools/call", "params": {"name": "screenshot", "arguments": {"path": "external_full.png", "full": True}}})
        print("SHOT2:", recv(server))

        # 8) shutdown
        send(server, {"id": 8, "method": "shutdown"})
        print("SHUT:", recv(server))

    finally:
        try:
            server.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
