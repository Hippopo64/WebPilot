from webpilot.tools import navigate, screenshot, extract_links

def run():
    print("[1] navigate:", navigate("https://example.com"))
    print("[2] screenshot:", screenshot("https://example.com", path="example_viewport.png", full=True))
    print("[3] extract_links:", extract_links("https://example.com"))

if __name__ == "__main__":
    run()
