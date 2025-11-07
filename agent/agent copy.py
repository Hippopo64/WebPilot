# agent/agent.py
import asyncio, sys, json, re
from contextlib import AsyncExitStack
from typing import Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client












    






# async def main():
#     server_path, input_path, output_path = args()

#     client = MCPClient()

#     try:
#         config = load_json_file(input_path)

#         await client.connect(server_path, mode="python")

#         url = config['url']
#         if not url or not isinstance(url, str):
#             raise ValueError("Input JSON must contain a valid 'url' string")
        
#         interactions = config.get("interactions", [])
#         options = config.get("options", {})
#         max_pages = options.get("max_pages", 1)

#         # Démo minimale : navigate → screenshot → get_html
#         print(f"\n🌍 navigate {url}")
#         res = await call_json(client, "tool_navigate", {"url": url})
#         print(json.dumps(res, indent=2))

#         print("\n▶️ run interactions")
#         r = await run_flow(client, interactions)
#         print(json.dumps(r, indent=2))
#         if not r.get("ok"):
#             raise RuntimeError(r.get("error"))
        
#         all_raw_data = {}
#         for name in config["collections_names"]:
#             all_raw_data[name] = []

#         for page_num in range(max_pages):
#             print(f"\n📄 get_html for page {page_num + 1}/{max_pages}")
#             content = await call_json(client, "tool_get_html", {})
#             html = content_to_html(content)
#             print("HTML length:", len(html))

#             schema_for_ia = {}
#             for name, schema in zip(config.get("collections_names", []), config.get("entity_schemas", [])):
#                 schema_for_ia[name] = schema
            
#             llm_map = await get_llm_map(client, schema_for_ia, html)

#             for collection_name in config.get("collections_names", []):
#                 collection_map = llm_map.get(collection_name, {})
#                 if not collection_map:
#                     print(f"⚠️ No LLM map found for collection '{collection_name}', skipping.")
#                     continue

#                 page_data = await scrape_page_with_map(client, collection_map, options.get("max_items_per_page", 500))

#                 if page_data:
#                     all_raw_data[collection_name].extend(page_data)
#                     print(f"Found {len(page_data)} items for '{collection_name}'")
#                 else:
#                     print(f"No items found for '{collection_name}' on this page.")

#             is_last_page = (page_num == max_pages - 1)
#             if is_last_page or not options.get("pagination", False):
#                 break
            
#             pagination_selector = None
#             for cmap in llm_map.values():
#                 if cmap.get("pagination_selector"):
#                     pagination_selector = cmap.get("pagination_selector")
#                     break
            
#             if not pagination_selector:
#                 print("⚠️ No pagination selector found in LLM map, stopping pagination.")
#                 break

#             click_success = await find_and_click_next(client, pagination_selector)
#             if not click_success:
#                 print("No 'next' button found, stopping pagination.")
#                 break
#             await asyncio.sleep(2)  # wait for page to load

#         all_clean_data = {}
#         all_reports = {}

#         for i, collection_name in enumerate(config.get("collections_names", [])):
#             collection_map = llm_map.get(collection_name, {})
#             if not collection_map:
#                 print(f"⚠️ No LLM map found for collection '{collection_name}', skipping.")
#                 continue

#             entity_schema = config.get("entity_schemas", [])[i]
#             print(f"\n run_scraping_loop for collection '{collection_name}'")
#             raw_data = all_raw_data.get(collection_name, [])
#             print(f"Total items scraped for '{collection_name}': {len(raw_data)}")

#             print(f"\n🧹 process_scraped_data for collection '{collection_name}'")
#             clean_data, quality_report = process_scraped_data(raw_data, entity_schema)
#             print(json.dumps(quality_report, indent=2))

#             all_clean_data[collection_name] = clean_data
#             all_reports[collection_name] = quality_report

#         final_output = build_final_output(config, all_clean_data, all_reports)
#         print(f"\n💾 Saving output to {output_path}")

#         save_output(output_path, final_output)
    
#     except Exception as e:
#         print("❌ Erreur lors de l'exécution de l'agent :", e)
#         save_output(output_path, {"status": "error", "message": str(e)})

#     finally:
#         print("\n🧹 Shutting down...")
#         try:
#             await client.close()
#         except Exception as e:
#             print("⚠️ Erreur lors de la fermeture du client :", e)
#         await asyncio.sleep(0.5)  # petite pause pour laisser le serveur se terminer


# if __name__ == "__main__":
#     asyncio.run(main())
