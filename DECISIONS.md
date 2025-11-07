# DECISIONS.md

Ce document présente les **décisions techniques** prises lors du développement du projet **WebPilot**, réalisé dans le cadre du test technique pour le poste de Développeur Full-Stack IA chez TW3 Partners.

Il explique les choix d'architecture (Serveur + Agent), les raisons derrière les implémentations clés, ainsi que les pistes d'amélioration.

----------

## 1. Architecture Générale : Serveur + Agent

L'objectif premier était de créer un serveur MCP exposant des outils de navigation. Le projet a ensuite évolué vers un système complet en deux parties :

1.  **Le Serveur (`src/webpilot/`) :** Un outil sûr construit avec **FastMCP** et **Playwright**. Il expose des outils d'intéractions (`click`, `fill`, `scrape_elements`, etc.) via `stdio`.
    
2.  **L'Agent (`agent/`) :** Autonome, il utilise les outils du serveur. Il pilote l'ensemble du processus de scraping en suivant un schéma JSON envoyé par l'user, en gérant la pagination et en appelant une IA pour l'analyse.
    

Cette séparation est une décision clé :

-   Le **Serveur** est "bête" et se concentre sur la fiabilité des interactions Playwright.
    
-   L'**Agent** est "intelligent" et orchestre la logique métier (que scraper ? où cliquer ?).
    

L'agent lui-même a été divisé en modules logiques (`scraper.py`, `processing.py`, `llm_map.py`, etc.) pour la maintenabilité, et la lisibilité.

----------

## 2. Choix Techniques Principaux

### `uv` pour la Gestion de Projet

Le projet utilise **`uv`** comme gestionnaire de dépendances et d'environnement.

-   **Rapidité :** `uv` est bien plus rapide que `pip` et `venv` combinés, ce qui accélère les cycles d'installation et de test.
    
-   **Simplicité :** Une seule commande (`uv sync`) gère l'environnement et les dépendances.
    
-   **Intégration MCP :** Il est recommandé par la documentation MCP et s'intègre parfaitement à l'inspecteur `mcp dev`.
    

### `LiteLLM` pour l'Abstraction de l'IA

Le choix de **`LiteLLM`** est stratégique.

-   **Flexibilité :** Il fournit une couche d'abstraction qui permet à l'agent d'appeler _n'importe quel_ fournisseur d'IA (OpenAI, Groq, Anthropic, Mistral) avec une seule interface.
    
-   **Simplicité :** Il gère la complexité des différents SDK et formats de requête, permettant à l'agent de se concentrer sur la logique du prompt.
    

### `Groq` pour l'Inférence

Pour le choix du LLM, **Groq** a été privilégié.

-   **Pertinence :** L'agent analyse le HTML _à chaque nouvelle page_. Un LLM lent rendrait la pagination inutilisable ou bien trop longue.
    
-   **Performance :** Groq utilise des LPU pour une inférence quasi-instantanée, ce qui est primordial pour un agent réactif, et donc pour ce projet.
    

### `Playwright` (Asynchrone)

L'ensemble du serveur (`tools.py`, `server.py`) utilise l'API **asynchrone** de Playwright.

-   **Compatibilité :** FastMCP s'exécute sur une boucle `asyncio`. Au début, l'utilisation de l'API synchrone de Playwright bloquait donc cette boucle et provoquait des crashs.


### Sécurité : L'appel LLM en tant qu'Outil Serveur

J'ai intentionnellement exposé l'IA comme un outil (`tool_generate_selectors`) dans le `server.py` plutôt que de l'appeler depuis l'Agent.

La raison principale est la sécurité :

- L'Agent ("le client") n'a jamais accès à la clé GROQ_API_KEY. Celle-ci reste protégée côté serveur, qui agit comme un proxy sécurisé. L'Agent envoie simplement le HTML et le schéma, et reçoit la carte en retour.

- Cela respecte aussi notre architecture et simule parfaitement une architecture microservice (où le service `WebPilot` appellerait un service `Selector-LLM` distinct).
    

----------

## 3. Décisions d'Implémentation de l'Agent

### Développement

L'agent a d'abord été développé **sans aucun appel LLM**. L'IA était simulée par une "carte" JSON générée à la main (`full_mock_map`).

-   **Objectif :** Valider toute la logique de l'agent (logique par page, scraping récursif, gestion des listes imbriquées, etc...) avant d'introduire la complexité d'un appel réseau à une IA. Cela permet aussi d'éviter de gaspiller des tokens pour rien.
    

### Logique "par Page"

L'agent est conçu pour être efficace. Au lieu de scraper un seul type de produit, il peut gérer plusieurs collections en un seul passage (ex: "citations" ET "top_tags").

-   La boucle `main` itère sur les **pages**.
    
-   _À l'intérieur_ de chaque page, l'agent itère sur **toutes les collections** demandées dans le schéma (`citations`, `top_tags`, etc.).
    
-   C'est beaucoup plus efficace que de relancer le script pour chaque type d'item.

Cette fonction n'était pas implémentée auparavant mais j'ai découvert un soucis. Sans ça, le processus était mauvais. En effet, si on scrape un premier élément pendant 5 pages, le script va s'arrêter à la 5ème page et le passer au second élément. Mais au lieu de commencer à la 1ère page, le script reprend à la 5ème, là où le premier s'est arrêté. 
On pourrait retourner sur le premier lien, mais si c'est une page dynamique, les éléments ont peut être changés. Si nos 2 éléments étaient sensés être inter connectés, ils ne le seront plus maintenant. De plus ça aurait fait des appels LLM en plus. C'est pourquoi on analyse tout sur chaque page.
    

### Robustesse du Nettoyage des Données

Le scraping échoue souvent à cause de données sales.

-   La fonction `convert_value` (et `clean_item_data`) a été conçue pour ne jamais crasher l'agent.
-   Elle renvoie un tuple `(valeur, erreur)`.
-   Si le nettoyage réussit, elle renvoie `(valeur_propre, None)`.
-   Si une conversion échoue (ex: `float("N/A")`), elle renvoie `(None, "message d'erreur")`.
-   Le `quality_report` final capture ces erreurs sans interrompre le scraping des autres items.
    

----------

## 4. Décisions d'Implémentation du Serveur

### Choix du Protocole : `stdio` vs. `SSE`

J'ai choisi le mode **`stdio`** (entrée/sortie standard) pour la communication entre l'agent et le serveur.

**Pourquoi `stdio` ?**

-   **Simplicité :** C'est le mode le plus direct pour un agent local. Il n'y a **pas de ports réseau** à gérer, pas de serveur HTTP à configurer, et pas de conflits.
    
-   **Tests Facilités :** Il s'intègre parfaitement avec l'outil d'inspection `mcp dev`, ce qui a rendu le débogage des outils Playwright beaucoup plus rapide.
    
-   **Propreté :** L'agent lance et "possède" le serveur. Quand l'agent s'arrête, le serveur s'arrête avec lui.
    

Le mode **`SSE` (via HTTP)** est plus complexe et mieux adapté à un serveur "persistant" en production (ex: un service cloud), ce qui n'était pas l'objectif ici, mais qu'il aurait fallu implémenter pour la partie 3.

### Robustesse des Sélecteurs (`.first`)

Les sites modernes affichent souvent plusieurs éléments pour un même bouton (ex: un pour mobile, un pour desktop), qui peuvent être non visibles.

-   Les outils `tool_click` et `tool_fill` ciblent le sélecteur, puis utilisent `.filter(visible=True).first` pour ne sélectionner que le premier élément actuellement visible par l'utilisateur.
    

### Gestion des Erreurs (`try/except`)

Un sélecteur invalide ou un élément non cliquable ne doit pas faire planter le serveur MCP.

-   Chaque outil dans `tools.py` est encapsulé dans un bloc `try/except`.
    
-   En cas d'échec (ex: timeout, élément non visible), l'outil capture l'exception et renvoie un JSON structuré `{ "ok": false, "error": "..." }`.

Cela permet d'assurer la continuité dans le processus.
    

### Logique d'Attente (Post-Clic)

Attendre après un clic est essentiel, mais seulement si le clic réussit.

-   L'attente (`asyncio.sleep(1)`) a été déplacée de `tools.py` vers `server.py`.
    
-   Elle n'est déclenchée que si l'outil `tool_click` renvoie `ok=True`, évitant des pauses inutiles lors d'échecs de clics.

Avant, dans `tools.py` on attendait à chaque clic, réussi ou pas, ce qui fait perdre beaucoup de temps lorsque l'on essaye plusieurs sélecteurs pour la page suivante.
    

### Séparation des Logs (`stderr`)

Les logs du serveur sont critiques pour le débogage.

-   Le serveur MCP utilise `stdout` pour envoyer ses réponses JSON à l'agent.
    
-   Le `logging` de Python a été configuré pour écrire sur `stderr`.
    
-   Cela empêche les logs "humains" de polluer le flux de données JSON "machine".
    
