from typing import Any, Dict, List, Tuple

from mcp import ClientSession

from agent.io_client import call_json
from agent.selectors_map import split_selector_attribute


async def scrape_item_recursive(session: ClientSession, base_selector: str, field_map: dict) -> dict:
    """
    Scrape a single item recursively based on the field map.
    Args:
        session: The MCP client session.
        base_selector (str): The base CSS selector for the item.
        field_map (dict): A mapping of field names to selectors (with optional @attribute).
    Returns:
        dict: A dictionary containing the scraped data for the item.
    """
    item_data = {}
    simple_fields = {}
    for field, selector in field_map.items():
        if isinstance(selector, str):
            simple_fields[field] = selector

    # simple_fields = {f: s for f, s in field_map.items() if isinstance(s, str)}
    # nested_fields = {f: s for f, s in field_map.items() if isinstance(s, dict)}
    
    for field, selector in simple_fields.items():
        sel_css, attr = split_selector_attribute(selector)
        if selector.strip() == "@self":
            sel_css = ""
            attr = "text-content"
        
        full_selector = f"{base_selector} {sel_css}".strip()
        scrape_args = {"selector": full_selector, "max_items": 1}
        if attr == "text-content":
            scrape_args["attribute"] = None
        elif attr:
            scrape_args["attribute"] = attr
        
        res = await call_json(session, "tool_scrape_elements", scrape_args)

        if res.get("ok") and res.get("items"):
            if res["items"]:
                item_data[field] = res["items"][0]
            else:
                item_data[field] = None
        else:
            item_data[field] = None
    
    nested_fields = {}
    for field, selector in field_map.items():
        if isinstance(selector, dict):
            nested_fields[field] = selector
    
    for field, sub_map in nested_fields.items():
        sub_item_selector = sub_map.get("item_selector")
        sub_fields_map = sub_map.get("fields", {})

        if not sub_item_selector:
            continue
        
        full_sub_selector = f"{base_selector} {sub_item_selector}".strip()
        item_data[field] = await scrape_page_with_map(session, {"item_selector": full_sub_selector, "fields": sub_fields_map})

    return item_data


async def scrape_page_with_map(session, llm_map: dict, max_items: int = 500) -> list[dict]:
    """
    Scrape the current page using a mapping of field names to selectors.
    Args:
        session: The MCP client session.
        llm_map (dict): A mapping of field names to CSS selectors (with optional @attribute).
        max_items (int): Maximum number of items to scrape per field.
    Returns:
        list[dict]: A list of dictionaries containing the scraped data.
    """
    item_sel = (llm_map.get("item_selector", "")).strip() or None
    fields_map = llm_map.get("fields", {})

    if not item_sel:
        raise ValueError("Item selector is required in llm_map for scraping")

    count = None
    res = await call_json(session, "tool_scrape_elements", {"selector": item_sel, "max_items": max_items, "attribute": "innerHTML"})
    if not res.get("ok"):
        return []
    
    count = min(res.get("count", 0), max_items)

    all_items_data = []
    for i in range(count):
        item_base_selector = f"{item_sel}:nth-of-type({i + 1})"
        item_data = await scrape_item_recursive(session, item_base_selector, fields_map)
        all_items_data.append(item_data)
    
    return all_items_data
