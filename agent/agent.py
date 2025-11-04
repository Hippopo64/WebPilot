# agent/agent.py
import asyncio, sys, json
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent, BlobResourceContents

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self, server_entry: str, mode: str = "python"):
        if mode == "python":
            params = StdioServerParameters(command="python", args=[server_entry], env=None)
        elif mode == "uv_mcp_dev":
            params = StdioServerParameters(command="uv", args=["run", "mcp", "dev", server_entry], env=None)
        else:
            raise ValueError("mode inconnu")

        stdio = await self.exit_stack.enter_async_context(stdio_client(params))
        self.stdio, self.write = stdio
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()


    async def call(self, tool: str, args: dict):
        return await self.session.call_tool(tool, args)

    async def close(self):
        await self.exit_stack.aclose()

def tool_result_to_dict(res) -> dict:
    """
    Convertit CallToolResult -> dict (ton payload).
    Essaie d'abord TextContent (JSON dans .text), puis BlobContent 'application/json'.
    Sinon, renvoie un dict brut avec le dump du contenu.
    """
    for c in getattr(res, "content", []) or []:
        # Cas le plus courant : FastMCP encode le dict en texte JSON
        if isinstance(c, TextContent):
            t = c.text or ""
            try:
                return json.loads(t)
            except Exception:
                return {"text": t}

        # Variante: contenu binaire JSON
        if isinstance(c, BlobResourceContents) and getattr(c, "mimeType", "") == "application/json":
            try:
                return json.loads(c.data.decode("utf-8"))
            except Exception:
                pass

    # Fallback: on renvoie le modèle brut
    return res.model_dump()

# --- helpers ---
def payload_to_html(payload: dict) -> str:
    # get_html peut renvoyer "html" ou "content" selon ta version serveur
    return payload.get("html") or payload.get("content") or ""

async def call_json(session, name, args=None):
    res = await session.call_tool(name, args or {})
    return tool_result_to_dict(res)

async def run_flow(session, interactions):
    for step in interactions:
        t = step.get("type")
        try:
            if t == "wait":
                await asyncio.sleep(step.get("ms", 500)/1000)
            elif t == "click":
                r = await call_json(session, "tool_click", {"selector": step["selector"]})
                if not r.get("ok") and not step.get("optional"):
                    return {"ok": False, "error": f"click failed: {r}"}
            elif t == "fill":
                r = await call_json(session, "tool_fill", {"selector": step["selector"], "text": step.get("text","")})
                if not r.get("ok"):
                    return {"ok": False, "error": f"fill failed: {r}"}
            elif t == "scroll":
                # nécessite tool_scroll côté serveur (sinon ignore)
                try:
                    r = await call_json(session, "tool_scroll", {
                        "direction": step.get("direction","down"),
                        "amount": step.get("amount",1),
                        "px": step.get("px",800)
                    })
                except Exception as e:
                    if not step.get("optional"):
                        return {"ok": False, "error": f"scroll failed: {e}"}
            else:
                return {"ok": False, "error": f"unknown step type: {t}"}
        except Exception as e:
            if step.get("optional"):
                continue
            return {"ok": False, "error": f"step '{t}' crashed: {e}"}
    return {"ok": True}
    

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python agent/agent.py src/webpilot/server.py")
        sys.exit(1)

    server_path = sys.argv[1]
    input_path = sys.argv[2] if len(sys.argv) > 2 else "agent/input.example.json"
    output_path = sys.argv[3] if len(sys.argv) > 3 else "output.json"
    client = MCPClient()
    try:
        await client.connect(server_path, mode="python")

        cfg = json.load(open(input_path, "r", encoding="utf-8"))
        url = cfg["url"]
        interactions = cfg.get("interactions", [])
        options = cfg.get("options", {})

        # Démo minimale : navigate → screenshot → get_html
        print(f"\n🌍 navigate {url}")
        res = await client.call("tool_navigate", {"url": url})
        print(json.dumps(tool_result_to_dict(res), indent=2))

        print("\n▶️ run interactions")
        r = await run_flow(client.session, interactions)
        print(json.dumps(r, indent=2))
        if not r.get("ok"):
            raise RuntimeError(r.get("error"))

        print("\n📄 get_html")
        html_res = await client.call("tool_get_html", {})
        payload = tool_result_to_dict(html_res)
        html = payload_to_html(payload)
        print("HTML length:", len(html))

        if options.get("screenshot"):
            snap_path = options.get("screenshot_path","after.png")
            print("\n📸 screenshot")
            snap = await client.call("tool_screenshot", {"path": snap_path, "full": False})
            print(json.dumps(tool_result_to_dict(snap), indent=2))

        # Output minimal (on remplira plus tard avec data & quality_report)
        out = {
            "status": "success",
            "url": url,
            "interactions_done": len(interactions),
            "html_length": len(html)
        }
        json.dump(out, open(output_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n✅ OK -> {output_path}")

    finally:
        print("\n🧹 Shutting down...")
        try:
            await client.close()
        except Exception as e:
            print("⚠️ Erreur lors de la fermeture du client :", e)
        await asyncio.sleep(0.5)  # petite pause pour laisser le serveur se terminer


if __name__ == "__main__":
    asyncio.run(main())
