# agent/agent.py
import asyncio, sys, json, re
from contextlib import AsyncExitStack
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent, BlobResourceContents


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
def payload_to_html(payload: dict) -> str:
    # get_html peut renvoyer "html" ou "content" selon ta version serveur
    return payload.get("html") or payload.get("content") or ""

async def call_json(session, name, args=None):
    res = await session.call_tool(name, args or {})
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


async def run_flow(session, interactions):
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
    

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python agent/agent.py src/webpilot/server.py")
        sys.exit(1)

    server_path = sys.argv[1]
    input_path = sys.argv[2] if len(sys.argv) > 2 else "agent/input.example.json"
    output_path = sys.argv[3] if len(sys.argv) > 3 else "output.json"
    client = MCPClient()
    try:
        await client.connect(server_path, mode="python")

        cfg = json.load(open(input_path, "r", encoding="utf-8"))
        url = cfg["url"]
        if not url or not isinstance(url, str):
            raise ValueError("Input JSON must contain a valid 'url' string")
        interactions = cfg.get("interactions", [])
        options = cfg.get("options", {})

        # Démo minimale : navigate → screenshot → get_html
        print(f"\n🌍 navigate {url}")
        res = await client.call("tool_navigate", {"url": url})
        print(json.dumps(tool_result_to_dict(res), indent=2))

        print("\n▶️ run interactions")
        r = await run_flow(client.session, interactions)
        print(json.dumps(r, indent=2))
        if not r.get("ok"):
            raise RuntimeError(r.get("error"))

        print("\n📄 get_html")
        html_res = await client.call("tool_get_html", {})
        payload = tool_result_to_dict(html_res)
        html = payload_to_html(payload)
        print("HTML length:", len(html))

        if options.get("screenshot"):
            snap_path = options.get("screenshot_path","after.png")
            print("\n📸 screenshot")
            snap = await client.call("tool_screenshot", {"path": snap_path, "full": False})
            print(json.dumps(tool_result_to_dict(snap), indent=2))

        # Output minimal (on remplira plus tard avec data & quality_report)
        out = {
            "status": "success",
            "url": url,
            "interactions_done": len(interactions),
            "html_length": len(html)
        }
        json.dump(out, open(output_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n✅ OK -> {output_path}")

    finally:
        print("\n🧹 Shutting down...")
        try:
            await client.close()
        except Exception as e:
            print("⚠️ Erreur lors de la fermeture du client :", e)
        await asyncio.sleep(0.5)  # petite pause pour laisser le serveur se terminer


if __name__ == "__main__":
    asyncio.run(main())
