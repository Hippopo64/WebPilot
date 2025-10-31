from playwright.sync_api import sync_playwright

def test_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://example.com")
        print("Titre de la page :", page.title())
        page.screenshot(path="capture.png")
        browser.close()
