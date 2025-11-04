from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url.strip())
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False

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
        if not is_valid_url(url):
            return {"ok": False, "error": "invalid URL", "details": f"'{url}' is not a valid URL. Must start with http:// or https:// and be valid."}
        
        resp = await page.goto(url, wait_until="load", timeout=15000)
        status = resp.status if resp else None
        if status and (status < 200 or status >= 400):
            return {"ok": False, "error": "bad status code", "status": status, "url": url}
        
        return {"ok": True, "status": resp.status if resp else None, "title": await page.title(), "url": page.url}
    
    except Exception as e:
        return {"ok": False, "error": "url not reachable", "details": str(e), "url": page.url}

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
        loc = page.locator(selector)
        target_loc = loc.filter(visible=True).first
        await target_loc.wait_for(state='visible', timeout=8000)
        try:
            async with page.expect_navigation(wait_until="load", timeout=5000):
                await target_loc.click()
        except Exception as nav_e:
            if "timeout" not in str(nav_e).lower():
                raise nav_e
            
            await page.wait_for_timeout(500)
            return {"ok": True, "url": page.url, "selector": selector, "note": "no navigation occurred"}

        return {"ok": True, "url": page.url, "selector": selector}
    
    except Exception as e:
        return {"ok": False, "error": "element not clickable", "details": str(e), "url": page.url, "selector": selector}

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
        loc = page.locator(selector)
        await loc.wait_for(state='attached', timeout=8000)

        if not await loc.is_enabled():
            return {"ok": False, "error": "element_disabled", "url": page.url, "selector": selector}
        if not await loc.is_editable():
            return {"ok": False, "error": "element_not_editable", "url": page.url, "selector": selector}
        
        await loc.fill(text)
        await page.wait_for_timeout(500)
        return {"ok": True, "url": page.url, "selector": selector, 'text': text}
    except Exception as e:
        return {"ok": False, "error": "element not editable or not fillable", "details": str(e), "url": page.url, "selector": selector}

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

