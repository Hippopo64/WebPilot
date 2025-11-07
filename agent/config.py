import argparse
import json
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse


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

def args() -> tuple[str, str, str]:
    p = argparse.ArgumentParser()
    p.add_argument("server_path")
    p.add_argument("input_path")
    p.add_argument("output_path")
    a = p.parse_args()
    return a.server_path, a.input_path, a.output_path
