import litellm
import os
import json
from dotenv import load_dotenv

# Load environment variables (e.g., GROQ_API_KEY) from .env
# Il va trouver le .env qui est à la racine WebPilot/
load_dotenv()

# Configure LiteLLM to be quieter
litellm.set_verbose_logger = False

# The model we are using, based on the free limits you found
GROQ_MODEL_ID = "groq/llama-3.3-70b-versatile"


def _build_prompt_messages(schema: dict, html_snippet: str) -> list:
    """Builds the prompt messages for the AI."""
    
    # We only provide a snippet of the HTML.
    # The token-per-minute limit is 12K. We aim for ~8K tokens for the HTML
    # (around 16000-24000 characters) to keep a safe margin.
    max_html_len = 20000 
    if len(html_snippet) > max_html_len:
        html_snippet = html_snippet[:max_html_len] + "..."

    # The expected output format
    output_format_description = """
    {
        "collection_name_1": {
            "item_selector": "the CSS selector for one item in the list",
            "fields": {
                "field_1": "CSS selector for this field",
                "field_2": "selector@attribute (e.g., 'a@href', 'img@src')",
                ...
            },
            "pagination_selector": "CSS selector for the 'next page' link (or null)"
        },
        "collection_name_2": {
            "item_selector": "...",
            "fields": { ... }
        },
        ...
    }
    """
    
    system_prompt = f"""
    You are an expert web scraper. Your mission is to analyze an HTML document and a JSON schema to generate a map of CSS selectors.
    - You MUST return a valid JSON object, and nothing else.
    - Selectors must be as robust and precise as possible.
    - Prefer 'data-*' attributes, 'id', 'aria-label', or semantic tags. Avoid fragile CSS classes (e.g., 'css-12345').
    - For attributes (links, images), use the 'selector@attribute' format (e.g., 'a.link@href', 'img.photo@src').
    - For text, just use the selector (e.g., 'span.price').
    - 'item_selector' MUST target the repeating container for *each* item in a collection.
    - 'pagination_selector' is the selector for the 'Next' link/button.
    - If a schema field is an object (nesting, e.g., "specifications"), do NOT generate a selector for it.
    - If a schema field is a list (e.g., "tags": [{{ "tag_name": "string" }}]), the 'item_selector' must target the *sub-list* item (e.g., 'a.tag') and the 'fields' must target the fields *within* that item (e.g., {{ "tag_name": "@self" }}).

    Here is the JSON output format you MUST follow:
    {output_format_description}
    """
    
    user_prompt = f"""
    Requested Schema:
    {json.dumps(schema, indent=2)}

    HTML Document (partial):
    {html_snippet}

    Generate the JSON selector map.
    """
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

#
# THIS IS THE FUNCTION YOU NEED TO EXPOSE AS AN MCP TOOL
#
async def generate_selectors(schema: dict, html: str) -> dict:
    """
    This is the function your MCP server will expose as 'tool_generate_selectors'.
    It takes the 'schema' and 'html' sent by the agent client.
    """
    
    # Simple argument validation
    if not isinstance(schema, dict) or not schema:
        return {"ok": False, "error": "Invalid or missing schema"}
    if not isinstance(html, str) or not html.strip():
        return {"ok": False, "error": "Invalid or missing HTML"}

    try:
        messages = _build_prompt_messages(schema, html)
        
        print(f"🤖 [Server] Calling Groq ({GROQ_MODEL_ID}) via LiteLLM to generate selectors...")
        
        response = await litellm.acompletion(
            model=GROQ_MODEL_ID,
            messages=messages,
            response_format={"type": "json_object"}, # This is the structured output!
            temperature=0.0, # We want a deterministic response
            timeout=120 # Allow time for analysis
        )
        
        # Extract the JSON content from the response
        json_content = response.choices[0].message.content
        selector_map = json.loads(json_content)
        
        print("✅ [Server] Selector map generated successfully.")
        
        # Return the result in MCP format
        return {"ok": True, "map": selector_map}
        
    except json.JSONDecodeError as e:
        print(f"❌ [Server] Error: The AI did not return valid JSON. {e}")
        return {"ok": False, "error": f"The AI did not return valid JSON: {e}"}
    except Exception as e:
        # Handle LiteLLM/Groq API errors, timeouts, etc.
        print(f"❌ [Server] Error during LiteLLM call: {e}")
        return {"ok": False, "error": f"Error calling AI: {str(e)}"}