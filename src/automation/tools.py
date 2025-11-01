from playwright.sync_api import sync_playwright

def _get_page():
    p = sync_playwright().start()
    browser = p.chromium.launch()
    page = browser.new_page()
    return p, browser, page

def navigate(url: str):
    p, browser, page = _get_page()
    try:
        resp = page.goto(url, wait_until="load", timeout=15000)
        return {"ok": True, "status": resp.status if resp else None, "title": page.title()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        browser.close(); p.stop()

def screenshot(url: str, path: str = "example_viewport.png", full: bool = False):
    p, browser, page = _get_page()
    try:
        page.goto(url, wait_until="load", timeout=15000)
        page.screenshot(path=path, full_page=full)
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        browser.close(); p.stop()

def extract_links(url: str, contains: str | None = None):
    p, browser, page = _get_page()
    try:
        page.goto(url, wait_until="load", timeout=15000)
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

        return {"ok": True, "count": len(links), "links": links, "links_sample": links[:5]}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": page.url}
    finally:
        browser.close(); p.stop()

        # A REFAIRE !!!!!


def click(url: str, selector: str):
    p, browser, page = _get_page()
    try:
        page.goto(url, wait_until="load", timeout=15000)
        page.wait_for_selector(selector, state='attached', timeout=8000)
        page.dispatch_event(selector, 'click')
        page.wait_for_timeout(3000) 
        return {"ok": True, "url": page.url, "selector": selector}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        browser.close(); p.stop()   


def fill(url: str, selector: str, text: str):
    p, browser, page = _get_page()
    try:
        page.goto(url, wait_until='load', timeout=15000)
        page.wait_for_selector(selector, state='attached', timeout=8000)
        try:
            page.fill(selector, text)
            page.wait_for_timeout(3000)
            return {"ok": True, "url": page.url, "selector": selector, 'text': text}
        except Exception as non_editable:
            return {"ok": False, "error": "Element not editable", "details": str(non_editable), url: page.url, "selector": selector}  
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        browser.close(); p.stop()


def get_html(url: str):
    p, browser, page = _get_page()
    try:
        page.goto(url, wait_until="load", timeout=15000)
        content = page.content()
        return {"ok": True, "length": len(content), "sample": content[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": page.url}
    finally:
        browser.close(); p.stop()   