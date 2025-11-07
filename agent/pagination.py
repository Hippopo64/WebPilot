from typing import Any, Dict, List, Optional, Union

from mcp import ClientSession

from agent.io_client import call_json
from agent.selectors_map import GENERIC_NEXT_SELECTORS, split_selector_attribute


async def try_click(session: ClientSession, selector: Optional[str]) -> bool:
    """
    Try to click on the given selector.
    """
    if not selector:
        return False
    
    sel_css, tmp = split_selector_attribute(selector) # tmp is ignored for clicking, bc click doesn't support attribute
    click = await call_json(session, "tool_click", {"selector": sel_css})

    if click.get("ok"):
        return True
    else:
        return False


async def find_and_click_next(session: ClientSession, llm_selector: str | list[str] | None) -> bool:
    """
    Try to find and click the "next" button using the provided LLM selector(s) first,
    then fall back to generic selectors if none of the LLM selectors work.
    """
    click_ok = False
    
    llm_selector_list = []
    if isinstance(llm_selector, str) and llm_selector.strip():
        llm_selector_list = [llm_selector.strip()] # we grab the single selector into a list
    # can be a list if the llm is not sure
    elif isinstance(llm_selector, list):
        llm_selector_list = llm_selector 

    if llm_selector_list:
        # loop through the llm selectors first
        for llm_sel in llm_selector_list:
            click_ok = await try_click(session, llm_sel)
            if click_ok:
                return True
    
    # If no LLM selectors worked, try generic selectors
    for gen_sel in GENERIC_NEXT_SELECTORS:
        click_ok = await try_click(session, gen_sel)
        if click_ok:
            return True
    return False