import asyncio
import json
from typing import Dict, List

from agent.config import args, load_json_file
from agent.flow import run_flow
from agent.io_client import MCPClient, call_json, content_to_html, save_output
from agent.pagination import find_and_click_next
from agent.processing import process_scraped_data
from agent.reporting import build_final_output
from agent.scraper import scrape_page_with_map
from agent.selectors_map import get_llm_map




async def _run() -> None:
    server_path, input_path, output_path = args()
    client = MCPClient()
    try:
        cfg = load_json_file(input_path)
        await client.connect(server_path, mode="python")

        url = cfg["url"]
        print(f"\n🌍 navigate {url}")
        print(json.dumps(await call_json(client, "tool_navigate", {"url": url}), indent=2))

        print("\n▶️ run interactions")
        r = await run_flow(client, cfg.get("interactions", []))
        print(json.dumps(r, indent=2))
        if not r.get("ok", False):
            raise RuntimeError(r.get("error", "interactions failed"))

        all_raw: Dict[str, List[dict]] = {name: [] for name in cfg["collections_names"]}
        options = cfg["options"]
        max_pages = int(options.get("max_pages", 1))
        use_pagination = bool(options.get("pagination", False))
        max_items_per_page = int(options.get("max_items_per_page", 500))

        for page_i in range(max_pages):
            print(f"\n📄 get_html for page {page_i+1}/{max_pages}")
            html_res = await call_json(client, "tool_get_html", {})
            html = content_to_html(html_res)
            print("HTML length:", len(html))

            schema_for_ia = dict(zip(cfg["collections_names"], cfg["entity_schemas"]))
            llm_map = await get_llm_map(client, schema_for_ia, html)

            for name in cfg["collections_names"]:
                cmap = llm_map.get(name) or {}
                if not cmap:
                    print(f"⚠️ No LLM map for '{name}', skipping.")
                    continue
                page_data = await scrape_page_with_map(client, cmap, max_items=max_items_per_page)
                if page_data:
                    all_raw[name].extend(page_data)
                    print(f"Found {len(page_data)} items for '{name}'")

            is_last = (page_i == max_pages - 1)
            if is_last or not use_pagination:
                break

            # récupère un sélecteur de pagination si présent dans l’une des collections
            pagination_selector = next(
                (c.get("pagination_selector") for c in llm_map.values() if c.get("pagination_selector")), None
            )
            if not await find_and_click_next(client, pagination_selector):
                print("No 'next' found, stopping pagination.")
                break

        all_clean, all_reports = {}, {}
        for i, name in enumerate(cfg["collections_names"]):
            raw = all_raw.get(name, [])
            print(f"\n run_scraping_loop for collection '{name}'")
            print(f"Total items scraped for '{name}': {len(raw)}")
            print(f"\n🧹 process_scraped_data for collection '{name}'")
            clean, report = process_scraped_data(raw, cfg["entity_schemas"][i])
            all_clean[name] = clean
            print(json.dumps(report, indent=2))
            all_reports[name] = report

        final = build_final_output(cfg, all_clean, all_reports)
        print(f"\n💾 Saving output to {output_path}")
        save_output(output_path, final)

    except Exception as e:
        print("❌ Erreur lors de l'exécution de l'agent :", e)
        save_output(output_path, {"status": "error", "message": str(e)})
    finally:
        print("\n🧹 Shutting down...")
        try:
            await client.close()
        except Exception as e:
            print("⚠️ Erreur lors de la fermeture du client :", e)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
