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
        # Load the input and start server
        cfg = load_json_file(input_path)
        await client.connect(server_path, mode="python")

        url = cfg["url"]
        print(f"\nNavigate {url}")
        print(json.dumps(await call_json(client, "tool_navigate", {"url": url}), indent=2))

        print("\nRunning interactions")
        r = await run_flow(client, cfg.get("interactions", []))
        print(json.dumps(r, indent=2))
        if not r.get("ok", False):
            raise RuntimeError(r.get("error", "interactions failed"))

        all_raw = {}
        # Initialize empty lists for each collection
        for name in cfg["collections_names"]:
            all_raw[name] = []
        

        options = cfg["options"]
        max_pages = int(options.get("max_pages", 1))
        use_pagination = bool(options.get("pagination", False))
        max_items_per_page = int(options.get("max_items_per_page", 500))

        # Start scraping loop
        for page_i in range(max_pages):
            print(f"\nget_html for page {page_i+1}/{max_pages}")
            html_res = await call_json(client, "tool_get_html", {})
            html = content_to_html(html_res)
            print("HTML length:", len(html))

            # schema for information extraction
            schema_for_ia = dict(zip(cfg["collections_names"], cfg["entity_schemas"]))
            llm_map = await get_llm_map(client, schema_for_ia, html)

            # loop over collections
            for name in cfg["collections_names"]:
                cmap = llm_map.get(name) or {} # cmap is the LLM map for this collection
                if not cmap:
                    print(f"No LLM map for '{name}', skipping.")
                    continue
                page_data = await scrape_page_with_map(client, cmap, max_items=max_items_per_page)
                if page_data:
                    all_raw[name].extend(page_data)
                    print(f"Found {len(page_data)} items for '{name}'")

            is_last = (page_i == max_pages - 1)
            if is_last or not use_pagination:
                break

            # Try to find and click the 'next' button
            pagination_selector = next(
                (c.get("pagination_selector") for c in llm_map.values() if c.get("pagination_selector")), None
            )

            # If click doesn't work, we stop
            if not await find_and_click_next(client, pagination_selector):
                print("No 'next' found, stopping pagination.")
                break

        # Process scraped data
        all_clean, all_reports = {}, {}
        # loop over collections
        for i, name in enumerate(cfg["collections_names"]):
            raw = all_raw.get(name, [])
            print(f"\nRun scraping loop for collection '{name}'")
            print(f"Total items scraped for '{name}': {len(raw)}")
            print(f"\nProcess scraped data for collection '{name}'")
            clean, report = process_scraped_data(raw, cfg["entity_schemas"][i])
            all_clean[name] = clean
            print(json.dumps(report, indent=2))
            all_reports[name] = report

        # Build final output
        final = build_final_output(cfg, all_clean, all_reports)
        print(f"\nSaving output to {output_path}")
        save_output(output_path, final)

    except Exception as e:
        print("Error while executing the agent:", e)
        save_output(output_path, {"status": "error", "message": str(e)})
    finally:
        print("\nShutting down...")
        try:
            await client.close()
        except Exception as close_e:
            err_str = str(close_e).lower()
            if "event loop is closed" in err_str or "bad file descriptor" in err_str:
                pass 
            else:
                print("Error while closing the client:", close_e)



def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
