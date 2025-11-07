import re
from typing import Any, Dict, List, Tuple
from datetime import datetime

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

        if isinstance(expected_type, list):
            sub_node = value
            if not isinstance(value, list):
                sub_node = []
                if value is None:
                    error_list.append(f"Field '{current_path}': missing")
                else:
                    error_list.append(f"Field '{current_path}': expected list but got {type(value)}")
            tmp_cleaned = []
            for i in range(len(sub_node)):
                sub_cleaned, sub_errors = clean_item_data(sub_node[i], expected_type[0], f"{current_path}[{i}]")
                tmp_cleaned.append(sub_cleaned)
                error_list.extend(sub_errors)
            
            cleaned[field] = tmp_cleaned

        elif isinstance(expected_type, dict):
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

