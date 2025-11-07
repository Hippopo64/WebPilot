from contextlib import AsyncExitStack
from typing import Any, Dict, Optional
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent.mcp_helpers import tool_result_to_dict


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


async def call_json(session: MCPClient, name, args=None):
    res = await session.call(name, args or {})
    return tool_result_to_dict(res)



def save_output(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def content_to_html(content: dict) -> str:
    return content.get("html") or content.get("content") or ""