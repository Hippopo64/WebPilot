from mcp import ClientSession
from typing import Optional, Tuple, List, Any, Dict

from agent.io_client import call_json


GENERIC_NEXT_SELECTORS: List[str] = [
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
    "text='›'",
]



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
    # full_mock_map = {
        
    #     "citations": { 
    #         "item_selector": "div.quote",
    #         "fields": {
    #             "texte": "span.text",
    #             "auteur": "small.author",
    #             "tags": { 
    #                 "item_selector": "a.tag",
    #                 "fields": { "nom_tag": "@self" }
    #             }
    #         },
    #         "pagination_selector": "li.next > a"
    #     },
        
    #     # --- CORRECTION 3 : Le sélecteur pour top_tags ---
    #     "top_tags": {
    #         # On sélectionne le CONTENEUR du tag
    #         "item_selector": "span.tag-item", 
    #         "fields": {
    #             # ET ENSUITE on cherche le tag à l'intérieur
    #             "nom_tag": "a.tag" 
    #         },
    #         "pagination_selector": None
    #     }
    #     # --- FIN CORRECTION 3 ---
    # }

    try: 
        tool_args = {"schema": schema, "html": html}

        response = await call_json(session, "tool_generate_selectors", tool_args)

        if response.get("ok"):
            final_map = response.get("map", {})

            filtered_map = {}
            for k, v in final_map.items():
                if k in schema:
                    filtered_map[k] = v

            return filtered_map
        else:
            print(f"⚠️ 'tool_generate_selectors' failed: {response.get('error', 'Invalid response')}")
    
    except Exception as e:
        print(f"❌ Error calling 'tool_generate_selectors': {e}")
    
    # print("🗺️ Carte des sélecteurs (simulée quotes.toscrape) reçue.")
    
    # # On filtre la carte pour ne renvoyer que ce qu'on a demandé
    # final_map = {k: v for k, v in full_mock_map.items() if k in schema}
    # return final_map


def split_selector_attribute(selector: str) -> tuple[str, Optional[str]]:
    """
    Split a selector string into selector and attribute.
    Example: "div.product@text" -> ("div.product", "text")
    """
    parts = selector.split("@")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return selector.strip(), None

