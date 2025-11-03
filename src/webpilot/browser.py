from playwright.async_api import async_playwright, Playwright, Browser, Page

async def start_browser() -> tuple[Playwright, Browser, Page]:
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True) 
    page = await browser.new_page()
    await page.set_viewport_size({"width": 1280, "height": 720})
    return p, browser, page

async def stop_browser(p, browser):
    if browser:
        await browser.close()
    if p:
        await p.stop()