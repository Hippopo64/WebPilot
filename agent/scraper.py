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

    # First, handle simple fields
    for field, selector in field_map.items():
        if isinstance(selector, str):
            simple_fields[field] = selector

    # Going through simple fields
    for field, selector in simple_fields.items():
        # Now separate css selector and attribute if sent by llm like this selector@attribute
        sel_css, attr = split_selector_attribute(selector)
        if selector.strip() == "@self":
            sel_css = ""
            attr = "text-content"
        
        full_selector = f"{base_selector} {sel_css}".strip()
        scrape_args = {"selector": full_selector, "max_items": 1} # construct scrape args that we send to tool
        if attr == "text-content":
            scrape_args["attribute"] = None
        elif attr:
            scrape_args["attribute"] = attr
        
        res = await call_json(session, "tool_scrape_elements", scrape_args) # scrape the element

        if res.get("ok") and res.get("items"):
            if res["items"]:
                item_data[field] = res["items"][0]
            else:
                item_data[field] = None
        else:
            item_data[field] = None
    
    #hande nested fields
    nested_fields = {}
    # Find nested fields
    for field, selector in field_map.items():
        if isinstance(selector, dict):
            nested_fields[field] = selector
    
    # loop on each nested field
    for field, sub_map in nested_fields.items():
        sub_item_selector = sub_map.get("item_selector") # get the item selector for the nested field
        sub_fields_map = sub_map.get("fields", {}) # get the fields map for the nested field

        # if no item selector, skip this field
        if not sub_item_selector:
            continue
        
        #but if there is one, proceed
        # construct full selector for the nested field
        full_sub_selector = f"{base_selector} {sub_item_selector}".strip()
        # recursively scrape the nested field on scrape_page_with_map because it is a mapping itself
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
    # Extract item selector and fields map
    item_sel = (llm_map.get("item_selector", "")).strip() or None # The main item selector
    fields_map = llm_map.get("fields", {}) # The mapping of fields to selectors that we send to the tool

    # If no item selector, raise error
    if not item_sel:
        raise ValueError("Item selector is required in llm_map for scraping")

    count = None
    # First, get the count of items to scrape
    res = await call_json(session, "tool_scrape_elements", {"selector": item_sel, "max_items": max_items, "attribute": "innerHTML"})
    if not res.get("ok"):
        return []
    
    count = min(res.get("count", 0), max_items)

    all_items_data = []
    # for each item, scrape recursively
    for i in range(count):
        item_base_selector = f"{item_sel}:nth-of-type({i + 1})" # construct base selector for the item n°i+1
        item_data = await scrape_item_recursive(session, item_base_selector, fields_map)
        all_items_data.append(item_data) # add the scraped item data to the list
    
    return all_items_data
