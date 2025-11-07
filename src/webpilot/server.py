# src/webpilot/server.py
from datetime import datetime
import sys
import logging
from logging import StreamHandler
from typing import Optional
import asyncio
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Tes modules
from webpilot.browser import start_browser, stop_browser
from webpilot import tools as T
from webpilot.llm_tools import generate_selectors

# ------------- Logging (recommandé par MCP) : vers STDERR -------------
logging.getLogger('asyncio').setLevel(logging.CRITICAL)  # Réduit le bruit d'asyncio
logger = logging.getLogger("webpilot.fastmcp")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(StreamHandler(sys.stderr))

# ------------- État navigateur partagé (1 browser / 1 page) -------------
P = BROWSER = PAGE = None

async def ensure_page():
    """Démarre Playwright une fois et réutilise la même page ensuite."""
    global P, BROWSER, PAGE
    if PAGE is None:
        P, BROWSER, PAGE = await start_browser()
        logger.info("browser_started")
    return PAGE

async def shutdown():
    """Arrêt propre quand le serveur se termine."""
    global P, BROWSER, PAGE
    try:
        await stop_browser(P, BROWSER)
        logger.info("browser_stopped")
    finally:
        P = BROWSER = PAGE = None

# ------------- Déclaration du serveur MCP (FastMCP) -------------
mcp = FastMCP("webpilot-mcp")

@mcp.tool()
async def tool_navigate(url: str):
    """
    This tool navigates to the specified URL.
    Args:
        url (str): The URL to navigate to.
    Returns:
        dict: A dictionary containing the result of the navigation attempt.
    """
    page = await ensure_page()
    try:
        res = await T.navigate(page, url)
    except Exception as e:
        res = {"ok": False, "error": "unable to navigate", "details": str(e), "url": url}
    logger.info(f"navigate ok={res.get('ok')} url={url}")
    return res

@mcp.tool()
async def tool_screenshot(path: Optional[str]=None, full: bool=False):
    """
    This tool takes a screenshot of the current page.
    Args:
        path (str, optional): The file path to save the screenshot to. Defaults to "snap.png".
        full (bool): Whether to capture the full page or just the viewport.
    Returns:
        dict: A dictionary containing the result of the screenshot attempt.
    """
    page = await ensure_page()
    try:
        if not path:
            path = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        res = await T.screenshot(page, path=path, full=full)
    except Exception as e:
        res = {"ok": False, "error": "unable to take screenshot", "details": str(e), "url": page.url, "path": path}
    logger.info(f"screenshot ok={res.get('ok')} path={path} full={full}")
    return res

@mcp.tool()
async def tool_extract_links(contains: Optional[str]=None):
    """
    This tool extracts all links from the current page, optionally filtering them by a substring.
    Args:
        contains (str, optional): A substring to filter links by. Defaults to None.
    Returns:
        dict: A dictionary containing the extracted links and related information.
    """
    page = await ensure_page()
    try:
        res = await T.extract_links(page, contains)
    except Exception as e:
        res = {"ok": False, "error": "unable to extract links", "details": str(e), "url": page.url}
    logger.info(f"extract_links ok={res.get('ok')} count={res.get('count')}")
    return res

@mcp.tool()
async def tool_fill(selector: str, text: str):
    """
    This tool fills a form field identified by a CSS selector with the provided text.
    Args:
        selector (str): The CSS selector of the form field to fill.
        text (str): The text to fill into the form field.
    Returns:
        dict: A dictionary containing the result of the fill attempt.
    """
    page = await ensure_page()
    try:
        res = await T.fill(page, selector, text)
    except Exception as e:
        res = {"ok": False, "error": "element not fillable", "details": str(e), "url": page.url, "selector": selector}
    logger.info(f"fill ok={res.get('ok')} selector={selector}")
    return res

@mcp.tool()
async def tool_click(selector: str):
    """
    This tool clicks on a specified element on the page.
    Args:
        selector (str): The CSS selector of the element to click.
    Returns:
        dict: A dictionary containing the result of the click attempt.
    """
    page = await ensure_page()

    try:
        res = await T.click(page, selector)
    except Exception as e:
        res = {"ok": False, "error": "element not clickable", "details": str(e), "url": page.url, "selector": selector}
    if res.get("ok"):
        await asyncio.sleep(1)  # Attente après clic réussi
    logger.info(f"click ok={res.get('ok')} selector={selector}")
    return res

@mcp.tool()
async def tool_get_html(save_path: Optional[str]=None):
    """
    This tool retrieves the HTML content of the current page.
    Args:
        save_path (str, optional): The file path to save the HTML content to. Defaults to None.
    Returns:
        dict: A dictionary containing the HTML content and related information.
    """
    page = await ensure_page()
    # Si T.get_html(page, save_path=...) existe, on l'utilise ; sinon on fallback.
    try:
        res = await T.get_html(page, save_path=save_path)
    except TypeError:
        res = await T.get_html(page)
        if res.get("ok") and save_path:
            html = await page.content()
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)
            res.setdefault("data", {})["saved_to"] = save_path
            res["data"]["length"] = len(html)
    logger.info(f"get_html ok={res.get('ok')} saved={bool(save_path)}")
    return res

@mcp.tool()
async def tool_scroll(direction: str="down", amount: int=1, px: int=800):
    """
    This tool scrolls the page in the specified direction by a certain amount.
    Args:
        direction (str): The direction to scroll ("down" or "up").
        amount (int): The number of times to scroll by the specified pixel amount.
        px (int): The number of pixels to scroll each time.
    Returns:
        dict: A dictionary containing the result of the scroll attempt.
    """
    page = await ensure_page()
    try:
        res = await T.scroll(page, direction=direction, amount=amount, px=px)
    except Exception as e:
        res = {"ok": False, "error": "unable to scroll", "details": str(e), "url": page.url}
    logger.info(f"scroll ok={res.get('ok')} direction={direction} amount={amount} px={px}")
    return res

@mcp.tool()
async def tool_scrape_elements(selector: str, attribute: str | None = None, max_items: int = 100) -> dict:
    """
    This tool scrapes elements from the page based on a CSS selector, optionally extracting a specific attribute.
    Args:
        selector (str): The CSS selector to identify elements.
        attribute (str, optional): The attribute to extract from each element. If None, extracts text content.
        max_items (int): The maximum number of elements to scrape.
    Returns:
        dict: A dictionary containing the result of the scrape attempt.
    """
    page = await ensure_page()
    try:
        res = await T.scrape_elements(page, selector, attribute=attribute, max_items=max_items)
    except Exception as e:
        res = {"ok": False, "error": "unable to scrape", "details": str(e), "url": page.url}
    logger.info(f"scrape ok={res.get('ok')} selector={selector} attribute={attribute} max_items={max_items}")
    return res

@mcp.tool()
async def tool_generate_selectors(schema: dict, html: str) -> dict:
    """
    This tool analyzes HTML and a schema to generate CSS selectors using an AI.
    Args:
        schema (dict): The JSON schema for data extraction.
        html (str): The HTML content of the page.
    Returns:
        dict: A dictionary containing the selector map or an error.
    """
    try:
        res = await generate_selectors(schema, html)
    except Exception as e:
        res = {"ok": False, "error": "unable to generate selectors", "details": str(e)}
    logger.info(f"generate_selectors ok={res.get('ok')}")
    return res


def main_stdio():
    """Execute server in stdio mode"""
    try:
        mcp.run_stdio()
    finally:
        asyncio.run(shutdown())

# Pour `uv run mcp dev src/webpilot/server.py` :
# Le CLI `mcp dev` importe ton module et attend que tu lui donnes un serveur FastMCP.
# On expose simplement l'objet `mcp` + un hook `__getattr__` si nécessaire.
def __getattr__(name: str):
    # Certains wrappers recherchent `app`/`server`. On renvoie mcp dans ces cas.
    if name in {"app", "server"}:
        return mcp
    raise AttributeError(name)

if __name__ == "__main__":
    # Lancement “direct” (facultatif) : uv run python -m webpilot.server
    mcp.run()
