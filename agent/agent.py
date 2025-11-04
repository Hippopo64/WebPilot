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

    # async def connect(self, server_script_path: str, python_cmd: str = "python"):
    #     # Construit les paramètres pour lancer le serveur en STDIO
    #     server_params = StdioServerParameters(
    #         command=python_cmd,
    #         args=[server_script_path],
    #         env=None
    #     )
    #     # Ouvre le transport stdio, puis crée la session client
    #     stdio = await self.exit_stack.enter_async_context(stdio_client(server_params))
    #     self.stdio, self.write = stdio
    #     self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
    #     await self.session.initialize()

    #     # Liste les tools exposés par le serveur
    #     resp = await self.session.list_tools()
    #     tools = [t.name for t in resp.tools]
    #     print("🛠️ Tools disponibles:", tools)
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
    

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python agent/agent.py src/webpilot/server.py")
        sys.exit(1)

    server_path = sys.argv[1]
    client = MCPClient()
    try:
        await client.connect("src/webpilot/server.py", mode="python")

        # Démo minimale : navigate → screenshot → get_html
        print("\n🌍 navigate example.com")
        res = await client.call("tool_navigate", {"url": "https://example.com"})
        print(json.dumps(tool_result_to_dict(res), indent=2))

        print("\n📸 screenshot")
        res = await client.call("tool_screenshot", {"path": "example.png", "full": False})
        print(json.dumps(tool_result_to_dict(res), indent=2))

        print("\n📄 get_html (length)")
        res = await client.call("tool_get_html", {})
        payload = tool_result_to_dict(res)
        print("HTML length:", len(payload.get("content","")))

    finally:
        print("\n🧹 Shutting down...")
        try:
            await client.close()
        except Exception as e:
            print("⚠️ Erreur lors de la fermeture du client :", e)
        await asyncio.sleep(0.5)  # petite pause pour laisser le serveur se terminer


if __name__ == "__main__":
    asyncio.run(main())
