from typing import Any, Dict, List
import asyncio

from agent.io_client import call_json


async def run_flow(session, interactions: list[dict]):
    for step in interactions:
        t = step.get("type")
        try:
            match t:
                case "wait":
                    await asyncio.sleep(step.get("ms", 500)/1000)
                case "click":
                    r = await call_json(session, "tool_click", {"selector": step["selector"]})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"click failed: {r}"}
                case "fill":
                    r = await call_json(session, "tool_fill", {"selector": step["selector"], "text": step.get("text","")})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"fill failed: {r}"}
                case "scroll":
                    r = await call_json(session, "tool_scroll", {"direction": step.get("direction","down"), "amount": step.get("amount",1), "px": step.get("px",800)})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"scroll failed: {r}"}
                case "navigate":
                    r = await call_json(session, "tool_navigate", {"url": step["url"]})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"navigate failed: {r}"}
                case "screenshot":
                    r = await call_json(session, "tool_screenshot", {"path": step.get("path","step_screenshot.png"), "full": step.get("full",False)})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"screenshot failed: {r}"}
                case "extract_links":
                    r = await call_json(session, "tool_extract_links", {"contains": step.get("contains")})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"extract_links failed: {r}"}
                case "get_html":
                    r = await call_json(session, "tool_get_html", {"save_path": step.get("save_path")})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"get_html failed: {r}"}
                case "scrape":
                    r = await call_json(session, "tool_scrape_elements", {"selector": step.get("selector"), "attribute": step.get("attribute"), "max_items": step.get("max_items",200)})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"scrape failed: {r}"}
                
                case _:
                    return {"ok": False, "error": f"unknown step type: {t}"}
                
        except Exception as e:
            if step.get("optional"):
                continue
            return {"ok": False, "error": f"step '{t}' crashed: {e}"}
    return {"ok": True}
