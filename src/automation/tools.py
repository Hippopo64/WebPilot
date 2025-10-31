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

def extract_links(url: str):
    p, browser, page = _get_page()
    try:
        page.goto(url, wait_until="load", timeout=15000)
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(a => ({text: (a.textContent||'').trim(), href: a.href}))"
        )
        return {"ok": True, "count": len(links), "links_sample": links[:5]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        browser.close(); p.stop()
