import json
from mcp.types import TextContent, BlobResourceContents

def tool_result_to_dict(res) -> dict:
    """
    Convert CallToolResult to dict
    Args:
        res: CallToolResult
    Returns:  
        out: dict
    """

    # Loop on contents to find JSON content
    for c in getattr(res, "content", []) or []:
        # If content is text 
        if isinstance(c, TextContent):
            t = c.text or ""
            try:
                # Try to parse JSON
                return json.loads(t)
            except Exception:
                return {"text": t}

        # If content is binary with JSON mime type
        if isinstance(c, BlobResourceContents) and getattr(c, "mimeType", "") == "application/json":
            try:
                return json.loads(c.data.decode("utf-8"))
            except Exception:
                pass
    
    # if content is not text or json encoded binary, return model dump to force a dict
    out = res.model_dump()
    return out