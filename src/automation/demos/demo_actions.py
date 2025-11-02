# AJOUTÉ : On importe les fonctions pour gérer le navigateur
from automation.tools import  navigate, click, fill, screenshot, extract_links
from automation.browser import start_browser, stop_browser

def run():
    # On initialise les variables pour le bloc finally
    p, browser, page = None, None, None
    try:
        # 1. On démarre le navigateur UNE SEULE FOIS
        p, browser, page = start_browser()

        # 2. On navigue vers la première URL
        url = "https://wikipedia.org/"
        print("[1] navigate:", navigate(page, url))

        # 3. On remplit (sur la page déjà ouverte)
        print("[2] fill:", fill(page, "input[name='search']", "Playwright"))

        # 4. On clique (sur la page déjà remplie)
        # L'URL va changer ici
        print("[3] click:", click(page, "button[type='submit']"))

        # 5. On prend le screenshot (de la nouvelle page de résultats)
        print("[4] screenshot:", screenshot(page, path="wikipedia_results.png", full=True))
        
        # 6. On va sur une nouvelle page pour extraire les liens
        print("[5] extract_links:", extract_links(page, contains="Playwright")["links_sample"])

    except Exception as e:
        print(f"UNE ERREUR S'EST PRODUITE: {e}")
        # On tente de prendre un screenshot d'erreur si possible
        if page:
            screenshot(page, path="error_screenshot.png")
            
    finally:
        # 7. On ferme le navigateur UNE SEULE FOIS, quoi qu'il arrive
        print("Fermeture du navigateur...")
        if 'page' in locals() and page: # Petit hack pour voir la page 5s avant fermeture
            page.wait_for_timeout(5000)
        stop_browser(p, browser)


if __name__ == "__main__":
    run()