# src/webpilot/demos/demo_scenario.py
import asyncio
from pathlib import Path
from urllib.parse import urlparse

from webpilot.browser import start_browser, stop_browser
from webpilot import tools as T

OUT = Path("demo_outputs")
OUT.mkdir(exist_ok=True)

async def run_demo():
    p, browser, page = await start_browser()
    try:
        # 1) Aller sur lequipe.fr
        print("➡️ navigate: https://lequipe.fr")
        r1 = await T.navigate(page, "https://lequipe.fr")
        print("   ", r1)

        # 2) Screenshot viewport
        vp_path = OUT / "00_lequipe_viewport.png"
        print(f"➡️ screenshot viewport → {vp_path}")
        r2 = await T.screenshot(page, path=str(vp_path), full=False)
        print("   ", r2)

        # 3) Extraire les liens et choisir le 1er lien EXTERNE
        print("➡️ extract_links")
        r3 = await T.extract_links(page)
        print(f"   found={r3.get('count')} sample={r3.get('links_sample')}")
        links = r3.get("links", []) or []
        external = None
        for l in links:
            href = (l.get("href") or "").strip()
            if not href:
                continue
            u = urlparse(href)
            if u.scheme in ("http", "https") and "lequipe.fr" not in (u.netloc or ""):
                external = href
                break
        if not external and links:
            external = links[0].get("href")

        if not external:
            print("❌ Aucun lien utilisable trouvé – arrêt démo.")
            return

        print(f"➡️ navigate external: {external}")
        r4 = await T.navigate(page, external)
        print("   ", r4)

        # 5) Screenshot full page
        full_path = OUT / "01_external_full.png"
        print(f"➡️ screenshot full → {full_path}")
        r5 = await T.screenshot(page, path=str(full_path), full=True)
        print("   ", r5)

        # (optionnel) Sauver l'HTML final pour preuve
        html_path = OUT / "01_external.html"
        print(f"➡️ save final HTML → {html_path}")
        html_res = await T.get_html(page)
        if html_res.get("ok"):
            html = html_res.get("content", "")
            html_path.write_text(html, encoding="utf-8")
            print("   ok:", {"length": len(html), "saved_to": str(html_path)})
        else:
            print("   get_html failed:", html_res)

        print("\n✅ DEMO OK — fichiers générés dans:", str(OUT.resolve()))

    finally:
        await stop_browser(p, browser)

if __name__ == "__main__":
    asyncio.run(run_demo())
