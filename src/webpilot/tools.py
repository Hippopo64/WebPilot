async def navigate(page, url: str) -> dict:
    """
    This tool navigates to the specified URL using the provided Playwright page.
    Args:
        page: The Playwright page object to perform navigation on.
        url (str): The URL to navigate to.
    Returns:
        dict: A dictionary containing the result of the navigation attempt.
    """
    try:
        resp = await page.goto(url, wait_until="load", timeout=15000)
        return {"ok": True, "status": resp.status if resp else None, "title": await page.title(), "url": page.url}
    except Exception as e:
        return {"ok": False, "error": "url not reachable", "details": str(e), "url": page.url}

# def navigate(page, url: str) -> dict:
#     """
#     This tool navigates to the specified URL using the provided Playwright page.
#     Args:
#         page: The Playwright page object to perform navigation on.
#         url (str): The URL to navigate to.
#     Returns:
#         dict: A dictionary containing the result of the navigation attempt.
#     """

#     try:
#         resp = page.goto(url, wait_until="load", timeout=15000)
#         return {"ok": True, "status": resp.status if resp else None, "title": page.title(), "url": page.url}
#     except Exception as e:
#         return {"ok": False, "error": "url not reachable", "details": str(e), "url": page.url}

async def extract_links(page, contains: str | None = None) -> dict:
    """
    This tool extracts all links from the current page, optionally filtering them by a substring.
    Args:
        page: The Playwright page object to extract links from.
        contains (str, optional): A substring to filter links by. Defaults to None.
    Returns:
        dict: A dictionary containing the extracted links and related information.
    """
    try:
        links = []
        for a in await page.query_selector_all("a[href]"):
            text = (await a.inner_text() or await a.text_content() or "").strip()
            href = await a.evaluate("el => el.href")
            links.append({"text": text, "href": href})
        if contains:
            needle = contains.lower()
            filtered_links = []
            for link in links:
                text = link.get("text", "").lower()
                if needle in text:
                    filtered_links.append(link)
            links = filtered_links

        return {"ok": True, "count": len(links), "links": links, "links_sample": links[:5], "url": page.url}
    except Exception as e:
        return {"ok": False, "error": "url not reachable", "details": str(e), "url": page.url}

# def extract_links(page, contains: str | None = None) -> dict:
#     """
#     This tool extracts all links from the current page, optionally filtering them by a substring.
#     Args:
#         page: The Playwright page object to extract links from.
#         contains (str, optional): A substring to filter links by. Defaults to None.
#     Returns:
#         dict: A dictionary containing the extracted links and related information.
#     """
#     try:
#         links = []
#         for a in page.query_selector_all("a[href]"):
#             text = (a.inner_text() or a.text_content() or "").strip()
#             href = a.evaluate("el => el.href")
#             links.append({"text": text, "href": href})
#         if contains:
#             needle = contains.lower()
#             filtered_links = []
#             for link in links:
#                 text = link.get("text", "").lower()
#                 if needle in text:
#                     filtered_links.append(link)
#             links = filtered_links

#         return {"ok": True, "count": len(links), "links": links, "links_sample": links[:5], "url": page.url}
#     except Exception as e:
#         return {"ok": False, "error": "url not reachable", "details": str(e), "url": page.url}
    
async def get_html(page) -> dict:
    """
    This tool retrieves the HTML content of the current page.
    Args:
        page: The Playwright page object to get HTML from.
    Returns:
        dict: A dictionary containing the HTML content and related information.
    """
    try:
        content = await page.content()
        return {"ok": True, "length": len(content), "content": content}
    except Exception as e:
        return {"ok": False, "error": "unable to get HTML", "details": str(e), "url": page.url}

# def get_html(page) -> dict:
#     """
#     This tool retrieves the HTML content of the current page.
#     Args:
#         page: The Playwright page object to get HTML from.
#     Returns:
#         dict: A dictionary containing the HTML content and related information.
#     """
#     try:
#         content = page.content()
#         return {"ok": True, "length": len(content), "sample": content[:500]}
#     except Exception as e:
#         return {"ok": False, "error": "unable to get HTML", "details": str(e), "url": page.url}

async def click(page, selector: str) -> dict:
    """
    This tool clicks on a specified element on the page.
    Args:
        page: The Playwright page object to perform the click on.
        selector (str): The CSS selector of the element to click.
    Returns:
        dict: A dictionary containing the result of the click attempt.
    """
    try:
        await page.wait_for_selector(selector, state='attached', timeout=8000)
        try:
            async with page.expect_navigation(wait_until="load", timeout=5000):
                await page.click(selector)
        except Exception as nav_e:
            if "Timeout" not in str(nav_e).lower():
                raise nav_e
            await page.wait_for_timeout(500) 

        return {"ok": True, "url": page.url, "selector": selector}
    
    except Exception as e:
        return {"ok": False, "error": "element not clickable", "details": str(e), "url": page.url, "selector": selector}

# def click(page, selector: str) -> dict:
#     """
#     This tool clicks on a specified element on the page.
#     Args:
#         page: The Playwright page object to perform the click on.
#         selector (str): The CSS selector of the element to click.
#     Returns:
#         dict: A dictionary containing the result of the click attempt.
#     """
#     try:
#         page.wait_for_selector(selector, state='attached', timeout=8000)
#         try:
#             with page.expect_navigation(wait_until="load", timeout=5000):
#                 page.click(selector)
#         except Exception as nav_e:
#             if "Timeout" not in str(nav_e).lower():
#                 raise nav_e
#             page.wait_for_timeout(500) 

#         return {"ok": True, "url": page.url, "selector": selector}
    
#     except Exception as e:
#         return {"ok": False, "error": "element not clickable", "details": str(e), "url": page.url, "selector": selector}

async def fill(page, selector: str, text: str) -> dict:
    """
    This tool fills a form field identified by a CSS selector with the provided text.
    Args:
        page: The Playwright page object to perform the fill on.
        selector (str): The CSS selector of the form field to fill.
        text (str): The text to fill into the form field.
    Returns:
        dict: A dictionary containing the result of the fill attempt.
    """
    try:
        await page.wait_for_selector(selector, state='attached', timeout=8000)
        await page.fill(selector, text)
        await page.wait_for_timeout(500)
        return {"ok": True, "url": page.url, "selector": selector, 'text': text}
    except Exception as e:
        return {"ok": False, "error": "element not editable or not fillable", "details": str(e), "url": page.url, "selector": selector}

# def fill(page, selector: str, text: str) -> dict:
#     """
#     This tool fills a form field identified by a CSS selector with the provided text.
#     Args:
#         page: The Playwright page object to perform the fill on.
#         selector (str): The CSS selector of the form field to fill.
#         text (str): The text to fill into the form field.
#     Returns:
#         dict: A dictionary containing the result of the fill attempt.
#     """
#     try:
#         page.wait_for_selector(selector, state='attached', timeout=8000)
#         page.fill(selector, text)
#         page.wait_for_timeout(500)
#         return {"ok": True, "url": page.url, "selector": selector, 'text': text}
#     except Exception as e:
#         return {"ok": False, "error": "element not editable or not fillable", "details": str(e), "url": page.url, "selector": selector}

async def screenshot(page, path: str = "example_viewport.png", full: bool = False) -> dict:
    """
    This tool takes a screenshot of the current page.
    Args:
        page: The Playwright page object to take the screenshot from.
        path (str): The file path to save the screenshot to.
        full (bool): Whether to capture the full page or just the viewport.
    Returns:
        dict: A dictionary containing the result of the screenshot attempt.
    """
    
    try:
        await page.screenshot(path=path, full_page=full)
        return {"ok": True, "path": path, "full": full, "url": page.url}
    except Exception as e:
        return {"ok": False, "error": "unable to take screenshot", "details": str(e), "url": page.url, "path": path}

# def screenshot(page, path: str = "example_viewport.png", full: bool = False) -> dict:
#     """
#     This tool takes a screenshot of the current page.
#     Args:
#         page: The Playwright page object to take the screenshot from.
#         path (str): The file path to save the screenshot to.
#         full (bool): Whether to capture the full page or just the viewport.
#     Returns:
#         dict: A dictionary containing the result of the screenshot attempt.
#     """
    
#     try:
#         page.screenshot(path=path, full_page=full)
#         return {"ok": True, "path": path, "full": full, "url": page.url}
#     except Exception as e:
#         return {"ok": False, "error": "unable to take screenshot", "details": str(e), "url": page.url, "path": path}