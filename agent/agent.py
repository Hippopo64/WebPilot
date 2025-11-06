# agent/agent.py
import asyncio, sys, json, re
from contextlib import AsyncExitStack
from typing import Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent, BlobResourceContents

GENERIC_NEXT_SELECTORS= [
    "a[rel='next']",
    "[data-test-id*='pagination-next' i]",
    "[data-testid*='pagination-next' i]",
    "[id*='pagination-next' i]",
    "[class*='next-page' i]",
    "[data-part*='next' i]",
    "button[rel='next']",
    "a[aria-label*='next' i]",
    "button[aria-label*='next' i]",
    "a:has-text('Next')",
    "a:has-text('Suivant')",
    "button:has-text('Next')",
    "button:has-text('Suivant')",
    "a.pagination-next",
    "button.pagination-next",
    "a[role='button']:has-text('Next')",
    "a[role='button']:has-text('Suivant')",
    "[aria-label*='next' i]",
    "[aria-label*='suivant' i]",
    "[class*='pagination-next' i]",
    "text='Next'",
    "text='Suivant'",
    "text='»'",
    "text='›'"
]


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self, server_entry: str, mode: str = "python"):
        if mode == "python":
            params = StdioServerParameters(command="python", args=[server_entry], env=None)
        elif mode == "uv_mcp_dev":
            params = StdioServerParameters(command="uv", args=["run", "mcp", "dev", server_entry], env=None)
        else:
            raise ValueError("mode inconnu")

        stdio = await self.exit_stack.enter_async_context(stdio_client(params))
        self.stdio, self.write = stdio
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()


    async def call(self, tool: str, args: dict):
        return await self.session.call_tool(tool, args)

    async def close(self):
        await self.exit_stack.aclose()


def tool_result_to_dict(res) -> dict:
    """
    Convertit CallToolResult -> dict (ton payload).
    Essaie d'abord TextContent (JSON dans .text), puis BlobContent 'application/json'.
    Sinon, renvoie un dict brut avec le dump du contenu.
    """
    for c in getattr(res, "content", []) or []:
        # Cas le plus courant : FastMCP encode le dict en texte JSON
        if isinstance(c, TextContent):
            t = c.text or ""
            try:
                return json.loads(t)
            except Exception:
                return {"text": t}

        # Variante: contenu binaire JSON
        if isinstance(c, BlobResourceContents) and getattr(c, "mimeType", "") == "application/json":
            try:
                return json.loads(c.data.decode("utf-8"))
            except Exception:
                pass

    # Fallback: on renvoie le modèle brut
    return res.model_dump()

# --- helpers ---
def content_to_html(content: dict) -> str:
    # get_html peut renvoyer "html" ou "content" selon ta version serveur
    return content.get("html") or content.get("content") or ""

async def call_json(session: MCPClient, name, args=None):
    res = await session.call(name, args or {})
    return tool_result_to_dict(res)

def is_http_url(url: str) -> bool:
    try:
        result = urlparse(url.strip())
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False
    

def normalize_options(options: dict) -> dict:
    if not isinstance(options, dict):
        options = {}

    res = {}
    if "pagination" in options:
        res["pagination"] = bool(options.get("pagination"))
    else:
        res["pagination"] = False
    
    if "max_pages" in options:
        try:
            val = int(options.get("max_pages"))
        except Exception:
            val = 1
        res["max_pages"] = max(1, val)
    else:
        res["max_pages"] = 1

    if "retry_failed" in options:
        res["retry_failed"] = bool(options.get("retry_failed"))
    else:
        res["retry_failed"] = True

    return res

def extract_schema(schema_obj: dict):
    """
    Extract the schema sub fields from the given schema object.
    Return collection_name the name of the collection, entity_schema how is the schema defined, metadata_schema the metadata schema.
    """
    if not isinstance(schema_obj, dict) or not schema_obj:
        raise ValueError("Schema object must be a non-empty dictionary")
    
    collection_name = []
    entity_schema = []
    metadata_schema = {}

    items = list(schema_obj.items())

    if isinstance(schema_obj.get("metadata"), dict):
        metadata_schema = schema_obj.get("metadata", {})
    else:
        metadata_schema = {}

    for k, v in items:
        if not isinstance(k, str) or not k.strip():
            raise ValueError("Collection names must be non-empty strings")
        if k.lower() == "metadata":
            continue
        
        collection_name.append(k)
        if isinstance(v, dict):
            if not v:
                raise ValueError(f"Schema for collection '{k}' cannot be an empty dictionary")
            entity_schema.append(v)
        elif isinstance(v, list):
            if not v or not isinstance(v[0], dict):
                raise ValueError(f"Schema for collection '{k}' must be a non-empty list of dictionaries")
            entity_schema.append(v[0])
        else:
            raise ValueError(f"Schema for collection '{k}' must be a dictionary or a list of dictionaries")
        
    if not collection_name:
        raise ValueError("At least one collection must be defined in the schema (other than metadata)")

    return collection_name, entity_schema, metadata_schema


def load_json_file(path: str) -> dict:
    """
    Load a JSON file from the given path, and extract the fields.
    """
    cfg = json.load(open(path, "r", encoding="utf-8"))
    url = cfg.get("url")
    if not url or not isinstance(url, str) or not is_http_url(url):
        raise ValueError("Input JSON must contain a valid 'url' string")
    names, schema, metadata = extract_schema(cfg.get("schema", {}))
    interactions = cfg.get("interactions", [])
    options = normalize_options(cfg.get("options", {}))

    return {
        "url": url,
        "collections_names": names,
        "entity_schemas": schema,
        "metadata": metadata,
        "interactions": interactions,
        "options": options
    }


def convert_to_int(value: str):
    m = re.search(r'([+-]?\d+)', value)
    if not m:
        raise ValueError(f"Value '{value}' is not a valid integer")
    return int(m.group(1))

def convert_to_float(value: str):
    cleaned_value = value.replace(' ', '').replace('\xa0', '')
    m = re.search(r'([+-]?\d+(?:[,.]\d+)?)', cleaned_value)
    if not m:
        raise ValueError(f"Value '{value}' is not a valid float")
    return float(m.group(1).replace(',', '.'))

def convert_to_bool(value: str):
    truth = ["true", "1", "yes", "oui", "vrai", "in stock", "disponible", "available", "en stock"]
    falsy = ["false", "0", "no", "non", "faux", "out of stock", "indisponible", "unavailable", "hors stock"]
    for k in truth:
        if k == value.strip().lower():
            return True
    for k in falsy:
        if k == value.strip().lower():
            return False
    raise ValueError(f"Value '{value}' is not a valid boolean")

def convert_to_datetime(value: str):
    dates = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"]
    for i in dates:
        try:
            return datetime.strptime(value, i).isoformat()
        except ValueError:
            continue
    raise ValueError(f"Value '{value}' is not a valid datetime")

def clean_string(value: str) -> str:
    if value is None:
        return None
    s = str(value).replace('\xa0', ' ').strip()
    if s != "":
        return s
    return None

def convert_value(value: str, expected_type: str):
    """
    Convert the given value to the expected type.
    Supported types: int, float, bool, datetime, str.
    """

    s = clean_string(value)
    if s is None:
        return (None, "Value is empty or only whitespace")

    integer = ["int", "integer", "entier"]
    float = ["float", "number", "nombre", "réel"]
    boolean = ["bool", "boolean", "booléen"]
    datetime = ["datetime", "date", "timestamp", "date-time"]
    string = ["str", "string", "texte", "text"]
    
    t = (expected_type or "string").lower()
    try:
        if t in string:
            return (s, None)
        if t in integer:
            return (convert_to_int(s), None)
        if t in float:
            return (convert_to_float(s), None)
        if t in boolean:
            return (convert_to_bool(s), None)
        if t in datetime:
            return (convert_to_datetime(s), None)
    except Exception as e:
        return (None, f"type={expected_type}, invalid value={value!r} error={str(e)}")
    
    return (None, f"unsupported type: {expected_type}")

def split_selector_attribute(selector: str) -> tuple[str, Optional[str]]:
    """
    Split a selector string into selector and attribute.
    Example: "div.product@text" -> ("div.product", "text")
    """
    parts = selector.split("@")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return selector.strip(), None

def normalize_fields_map(fields_map: dict, prefix: str = "") -> dict[str, list[str]]:
    """
    Normalize the fields map to ensure each field maps to a list of selectors.
    The llm return a dict like : 
    {
        "title": "div.product-title",
        "price": ["span.price", "div.cost"],
        "specs": {"cpu": "div.cpu", "ram": "div.ram"}
    }
    Returns:
        dict[str, list[str]]: A normalized fields map like : 
    {
        "title": ["div.product-title"],
        "price": ["span.price", "div.cost"],
        "specs.cpu": ["div.cpu"],
        "specs.ram": ["div.ram"]
    }
    """
    if not isinstance(fields_map, dict) or not fields_map:
        raise ValueError("Fields map cannot be empty")
    
    res = {}
    for field, sel in fields_map.items():
        current_field = field
        if not sel:
            raise ValueError(f"Selector for field '{field}' cannot be empty")

        if prefix:
            current_field = f"{prefix}.{field}"
        if isinstance(sel, str):
            res[current_field] = [sel]
        elif isinstance(sel, list):
            for s in sel:
                if not isinstance(s, str):
                    raise ValueError(f"Selector for field '{field}' must be a string or a list of strings")
            res[current_field] = sel
        elif isinstance(sel, dict):
            res.update(normalize_fields_map(sel, prefix=current_field))
        else:
            raise ValueError(f"Selector for field '{field}' must be a string or a list of strings")
    
    return res


async def scrape_page_with_map(session, llm_map: dict, max_items: int = 500) -> list[dict]:
    """
    Scrape the current page using a mapping of field names to selectors.
    Args:
        session: The MCP client session.
        llm_map (dict): A mapping of field names to CSS selectors (with optional @attribute).
        max_items (int): Maximum number of items to scrape per field.
    Returns:
        list[dict]: A list of dictionaries containing the scraped data.
    """
    item_sel = (llm_map.get("item_selector", "")).strip() or None
    fields_map = normalize_fields_map(llm_map.get("fields", {}))

    count = None
    if item_sel:
        res = await call_json(session, "tool_scrape_elements", {"selector": item_sel, "max_items": max_items})
        if res.get("ok"):
            count = res.get("count", 0)
        else:
            count = None

    columns: dict[str, list] = {}
    for field, selectors in fields_map.items():
        items = []
        if isinstance(selectors, list) and selectors:
            for sel in selectors:
                vals = []
                sel_css, attr = split_selector_attribute(sel)
                if item_sel and sel_css:
                    full_selector = f"{item_sel} {sel_css}".strip()
                else:
                    full_selector = sel_css
                res = await call_json(session, "tool_scrape_elements", {"selector": full_selector, "attribute": attr, "max_items": max_items})
                if res.get("ok"):
                    vals = res.get("items", [])
                if vals:
                    items = vals
                    break
        else:
            raise ValueError(f"Selectors for field '{field}' must be a non-empty list of strings")
        
        columns[field] = items
        if count is None and items:
            count = len(items)


    count = count or 0

    data = []
    for i in range(count):
        row = {}
        for field, items in columns.items():
            if "." in field: # to change the . into {}
                parts = field.split(".") #specs.cpu.cpu1.brand for example is separated
                current = row
                size = len(parts) #number of parts
                for j in range(size - 1): # we go through all parts except the last one
                    if parts[j] not in current: #if the part does not exist yet
                        current[parts[j]] = {} #we create
                    current = current[parts[j]] # we go to next part
                if i < len(items):
                    current[parts[size - 1]] = items[i] # Remember that parts contains the name and items the value
                else:
                    current[parts[size - 1]] = None
            else:
                if i < len(items):
                    row[field] = items[i]
                else:
                    row[field] = None
        data.append(row)

    return data


def clean_item_data(raw_node: dict, schema_node: dict, path_prefix: str = "") -> tuple[dict, list[str]]:
    """
    Clean and validate a single item against the schema.
    Args:
        raw_node (dict): The raw item data.
        schema_node (dict): The schema for the item.
    Returns:
        tuple[dict, list[str]]: The cleaned item data and a list of fields with errors.
    """
    cleaned = {}
    error_list = []

    for field, expected_type in schema_node.items():
        if path_prefix:
            current_path = f"{path_prefix}.{field}"
        else:
            current_path = field
        
        value = raw_node.get(field)

        if isinstance(expected_type, dict):
            sub_node = value
            if not isinstance(value, dict):
                sub_node = {}
                if value is None:
                    error_list.append(f"Field '{current_path}': missing")
                else:
                    error_list.append(f"Field '{current_path}': expected dict but got {type(value)}") 

            sub_cleaned, sub_errors = clean_item_data(sub_node, expected_type, current_path)
            cleaned[field] = sub_cleaned
            error_list.extend(sub_errors)

        elif value is None:
            cleaned[field] = None
            error_list.append(f"Field '{current_path}': missing")

        else:
            conv_value, error = convert_value(value, expected_type)
            if error:
                cleaned[field] = None
                error_list.append(f"Field '{current_path}': {error}")
            else:
                cleaned[field] = conv_value

    return cleaned, error_list


def process_scraped_data(raw_data: list[dict], entity_schema: dict) -> tuple[list[dict], dict]:
    """
    Process the raw scraped data according to the entity schema.
    Args:
        raw_data (list[dict]): The raw scraped data.
        entity_schema (dict): The schema defining expected types for each field.
    Returns:
        list[dict]: The processed data with converted types.
        dict: The quality report
    """
    clean_data = []

    total_items = len(raw_data)
    complete_items = 0
    error_fields = {}
    conversion_errors = []

    for item in raw_data:
        cleaned_item, errors = clean_item_data(item, entity_schema)
        clean_data.append(cleaned_item)
        conversion_errors.extend(errors)

        if not errors:
            complete_items += 1
        else:
            for err in errors:
                if "Field '" in err:
                    field_name = err.split("'")[1]
                    error_fields[field_name] = error_fields.get(field_name, 0) + 1

    missing_list = []
    for field, count in error_fields.items():
        missing_list.append(f"{field}: {count} items")

    quality_report = {
        "total_items": total_items,
        "complete_items": complete_items,
        "completion_rate": round(complete_items / total_items, 3) if total_items > 0 else 0,
        "missing_fields": missing_list,
        "errors": list(set(conversion_errors))
    }

    return clean_data, quality_report


async def try_click(session: ClientSession, selector: str) -> bool:
    if not selector:
        return False
    sel_css, tmp = split_selector_attribute(selector)
    click = await call_json(session, "tool_click", {"selector": sel_css})

    if click.get("ok"):
        return True
    else:
        return False
    
async def find_and_click_next(session: ClientSession, llm_selector: str | list[str] | None) -> bool:
    click_ok = False
    
    llm_selector_list = []
    if isinstance(llm_selector, str) and llm_selector.strip():
        llm_selector_list = [llm_selector.strip()]
    elif isinstance(llm_selector, list):
        llm_selector_list = llm_selector

    if llm_selector_list:
        for llm_sel in llm_selector_list:
            click_ok = await try_click(session, llm_sel)
            if click_ok:
                return True
    
    for gen_sel in GENERIC_NEXT_SELECTORS:
        click_ok = await try_click(session, gen_sel)
        if click_ok:
            return True
    return False





async def run_flow(session, interactions: list[dict]):
    for step in interactions:
        t = step.get("type")
        try:
            match t:
                case "wait":
                    await asyncio.sleep(step.get("ms", 500)/1000)
                case "click":
                    r = await call_json(session, "tool_click", {"selector": step["selector"]})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"click failed: {r}"}
                case "fill":
                    r = await call_json(session, "tool_fill", {"selector": step["selector"], "text": step.get("text","")})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"fill failed: {r}"}
                case "scroll":
                    r = await call_json(session, "tool_scroll", {"direction": step.get("direction","down"), "amount": step.get("amount",1), "px": step.get("px",800)})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"scroll failed: {r}"}
                case "navigate":
                    r = await call_json(session, "tool_navigate", {"url": step["url"]})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"navigate failed: {r}"}
                case "screenshot":
                    r = await call_json(session, "tool_screenshot", {"path": step.get("path","step_screenshot.png"), "full": step.get("full",False)})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"screenshot failed: {r}"}
                case "extract_links":
                    r = await call_json(session, "tool_extract_links", {"contains": step.get("contains")})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"extract_links failed: {r}"}
                case "get_html":
                    r = await call_json(session, "tool_get_html", {"save_path": step.get("save_path")})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"get_html failed: {r}"}
                case "scrape":
                    r = await call_json(session, "tool_scrape_elements", {"selector": step.get("selector"), "attribute": step.get("attribute"), "max_items": step.get("max_items",200)})
                    if not r.get("ok") and not step.get("optional"):
                        return {"ok": False, "error": f"scrape failed: {r}"}
                
                case _:
                    return {"ok": False, "error": f"unknown step type: {t}"}
                
        except Exception as e:
            if step.get("optional"):
                continue
            return {"ok": False, "error": f"step '{t}' crashed: {e}"}
    return {"ok": True}
    

def args():
    if len(sys.argv) < 2:
        print("Usage: uv run python agent/agent.py src/webpilot/server.py [input.json] [output.json]")
        sys.exit(1)

    server_path = sys.argv[1]
    input_path = sys.argv[2] if len(sys.argv) > 2 else "agent/input.example.json"
    output_path = sys.argv[3] if len(sys.argv) > 3 else "output.json"
    return server_path, input_path, output_path

def save_output(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def run_scraping_loop(session: ClientSession, llm_map: dict, options: dict):
    """
    Do the main loop, scraping elements sent by the llm, doing it through number of pages asked by user
    Args:
        session: The MCP client session.
        llm_map (dict): A mapping of field names to CSS selectors (with optional @attribute).
        options (dict): Options for pagination and retries.
    Returns:
        list[dict]: The scraped data.
    """
    all_data = []
    max_pages = options.get("max_pages", 1)

    for page_num in range(max_pages):
        print(f"Scraping page {page_num + 1}/{max_pages}")
        page_data = await scrape_page_with_map(session, llm_map)
        if not page_data:
            print("No data scraped on this page, stopping.")
            break
        all_data.extend(page_data)

        if page_num == max_pages - 1:
            is_last_page = True
        else:
            is_last_page = False

        if is_last_page or not options.get("pagination", False):
            break

        click_success = await find_and_click_next(session, llm_map.get("pagination_selector"))
        if not click_success:
            print("No 'next' button found, stopping pagination.")
            break

        await asyncio.sleep(2)  # wait for page to load

    return all_data

async def get_llm_map(session: ClientSession, schema: dict, html: str) -> dict:
    """
    Extract the LLM map from the HTML content using the provided schema.
    Args:
        session: The MCP client session.
        schema: The schema to use for extraction.
        html: The HTML content to extract data from.
    Returns:
        dict: The extracted LLM map.
    """
    full_mock_map = {
        # La clé "citations" doit correspondre à celle du input.json
        "citations": { 
            
            # Le conteneur pour UNE SEULE citation
            "item_selector": "div.quote",
            
            # Les champs à l'intérieur de l'item_selector
            "fields": {
                "texte": "span.text",
                "auteur": "small.author"
            },
            
            # Le bouton pour la page suivante
            "pagination_selector": "li.next > a"
        }
    }
    
    print("🗺️ Carte des sélecteurs (simulée quotes.toscrape) reçue.")
    
    # On filtre la carte pour ne renvoyer que ce qu'on a demandé
    final_map = {k: v for k, v in full_mock_map.items() if k in schema}
    return final_map

def build_final_output(config: dict, cleaned_data: dict, quality_report: dict) -> dict:
    metadata = config.get("metadata", {})
    if "data-extraction" in metadata:
        metadata["data-extraction"] = datetime.now().isoformat()
    if "nb_resultats" in  metadata:
        total_results = 0
        for items in cleaned_data.values():
            total_results += len(items)
        metadata["nb_resultats"] = total_results

    data_object = cleaned_data.copy()
    data_object["metadata"] = metadata

    final_report = {}
    num_collections = len(quality_report)
    if num_collections == 1:
        final_report = list(quality_report.values())[0]
    elif num_collections > 1:
        final_report = quality_report.copy()
        summary_total = 0
        summary_complete = 0
        for report in quality_report.values():
            summary_total += report.get("total_items", 0)
            summary_complete += report.get("complete_items", 0)

        summary_rate = 0
        if summary_total > 0:
            summary_rate = round(summary_complete / summary_total, 3)

        final_report["summary"] = {
            "total_items": summary_total,
            "complete_items": summary_complete,
            "completion_rate": summary_rate
        }

    output = {
        "status": "success",
        "data" : data_object,
        "quality_report": final_report
    }
    return output


async def main():
    server_path, input_path, output_path = args()

    client = MCPClient()

    try:
        config = load_json_file(input_path)

        await client.connect(server_path, mode="python")

        url = config['url']
        if not url or not isinstance(url, str):
            raise ValueError("Input JSON must contain a valid 'url' string")
        
        interactions = config.get("interactions", [])
        options = config.get("options", {})

        # Démo minimale : navigate → screenshot → get_html
        print(f"\n🌍 navigate {url}")
        res = await call_json(client, "tool_navigate", {"url": url})
        print(json.dumps(res, indent=2))

        print("\n▶️ run interactions")
        r = await run_flow(client, interactions)
        print(json.dumps(r, indent=2))
        if not r.get("ok"):
            raise RuntimeError(r.get("error"))

        print("\n📄 get_html")
        content = await call_json(client, "tool_get_html", {})
        html = content_to_html(content)
        print("HTML length:", len(html))

        schema_for_ia = {}
        for name, schema in zip(config.get("collections_names", []), config.get("entity_schemas", [])):
            schema_for_ia[name] = schema
        
        llm_map = await get_llm_map(client.session, schema_for_ia, html)

        all_clean_data = {}
        all_reports = {}

        for i, collection_name in enumerate(config.get("collections_names", [])):
            collection_map = llm_map.get(collection_name, {})
            if not collection_map:
                print(f"⚠️ No LLM map found for collection '{collection_name}', skipping.")
                continue

            entity_schema = config.get("entity_schemas", [])[i]
            print(f"\n run_scraping_loop for collection '{collection_name}'")
            raw_data = await run_scraping_loop(client, collection_map, options)
            print(f"Total items scraped for '{collection_name}': {len(raw_data)}")

            print(f"\n🧹 process_scraped_data for collection '{collection_name}'")
            clean_data, quality_report = process_scraped_data(raw_data, entity_schema)
            print(json.dumps(quality_report, indent=2))

            all_clean_data[collection_name] = clean_data
            all_reports[collection_name] = quality_report

        final_output = build_final_output(config, all_clean_data, all_reports)
        print(f"\n💾 Saving output to {output_path}")

        save_output(output_path, final_output)
    
    except Exception as e:
        print("❌ Erreur lors de l'exécution de l'agent :", e)
        save_output(output_path, {"status": "error", "message": str(e)})

    finally:
        print("\n🧹 Shutting down...")
        try:
            await client.close()
        except Exception as e:
            print("⚠️ Erreur lors de la fermeture du client :", e)
        await asyncio.sleep(0.5)  # petite pause pour laisser le serveur se terminer


if __name__ == "__main__":
    asyncio.run(main())
