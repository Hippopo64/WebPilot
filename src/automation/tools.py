from playwright.sync_api import sync_playwright

def navigate(page, url: str):
    try:
        resp = page.goto(url, wait_until="load", timeout=15000)
        return {"ok": True, "status": resp.status if resp else None, "title": page.title(), "url": page.url}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": page.url}

def extract_links(page, contains: str | None = None):
    try:
        links = []
        for a in page.query_selector_all("a[href]"):
            text = (a.inner_text() or a.text_content() or "").strip()
            href = a.evaluate("el => el.href")
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
        return {"ok": False, "error": str(e), "url": page.url}
    
def get_html(page):
    try:
        content = page.content()
        return {"ok": True, "length": len(content), "sample": content[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": page.url}


# REFAIRE CAR PROBLEME AVEC TIMEOUT SI TROP LONG
def click(page, selector: str):
    try:
        page.wait_for_selector(selector, state='attached', timeout=8000)
        try:
            with page.expect_navigation(wait_until="load", timeout=5000):
                page.dispatch_event(selector, 'click')
        except Exception as nav_e:
            if "Timeout" not in str(nav_e).lower():
                raise nav_e
            page.wait_for_timeout(500)
        return {"ok": True, "url": page.url, "selector": selector}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": page.url}

def fill(page, selector: str, text: str):
    try:
        page.wait_for_selector(selector, state='attached', timeout=8000)
        page.fill(selector, text)
        page.wait_for_timeout(500)
        return {"ok": True, "url": page.url, "selector": selector, 'text': text}
    except Exception as e:
        return {"ok": False, "error": "element not editable or not fillable", "details": str(e), "url": page.url, "selector": selector}

def screenshot(page, path: str = "example_viewport.png", full: bool = False):
    try:
        page.screenshot(path=path, full_page=full)
        return {"ok": True, "path": path, "full": full, "url": page.url}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": page.url}