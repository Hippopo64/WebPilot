from playwright.sync_api import sync_playwright

def start_browser():
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True) 
    page = browser.new_page()
    page.set_viewport_size({"width": 1280, "height": 720})
    return p, browser, page

def stop_browser(p, browser):
    if browser:
        browser.close()
    if p:
        p.stop()