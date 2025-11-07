import json
from mcp.types import TextContent, BlobResourceContents

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