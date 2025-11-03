# server.py
from mcp.server.fastmcp import FastMCP
import sys
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
mcp = FastMCP("DemoServer")

@mcp.tool()
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    logging.info(f"Appel de add({a}, {b})")
    return a + b

@mcp.resource("greeting://{name}")
async def get_greeting(name: str) -> str:
    """Return a greeting for a name."""
    logging.info(f"Appel de get_greeting({name})")
    return f"Hello, {name}!"

if __name__ == "__main__":
    logging.info("Démarrage du serveur 'DemoServer'...")
    
    # --- LA CORRECTION EST ICI ---
    mcp.run(transport='stdio')
    # --- FIN DE LA CORRECTION ---