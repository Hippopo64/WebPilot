
# DECISIONS.md

Ce document présente les **décisions techniques** prises lors du développement du projet **WebPilot **, réalisé dans le cadre du test technique pour le poste de Développeur Full-Stack IA chez TW3 Partners.  
Il explique les choix d’architecture, les raisons derrière certaines implémentations, ainsi que les pistes d’amélioration envisagées.

---

## 🎯 1. Objectif du projet

L’objectif du projet est de concevoir un **serveur MCP (Model Context Protocol)** permettant d’exposer plusieurs outils d’automatisation de navigateur.  
Ces outils permettent à une IA ou à un utilisateur d’interagir avec une page web : navigation, clics, remplissage de champs, extraction de liens ou captures d’écran.  
Le tout repose sur le **SDK officiel du MCP**, et communique via le protocole **stdio** pour faciliter les tests locaux et l’intégration dans des environnements compatibles MCP.

---

## 🧩 2. Architecture et organisation du code

Le projet est organisé de manière modulaire afin de séparer clairement la logique serveur, les outils et la gestion du navigateur.

**Différents fichiers :**
browser.py → Gestion du navigateur Playwright (lancement, arrêt)
tools.py → Fonctions des outils (navigate, click, fill, etc.)
server.py → Serveur MCP exposant les tools via FastMCP
demo_scenario.py → Script de démonstration automatisé


**Raisons de cette organisation :**
- `browser.py` : propose des fonctions pour lancer et ferme un navigateur, afin de permettre une continuité entre les étapes 
- `tools.py` : regroupe les fonctions principales du projet (navigate, screenshot, extract_links, etc.), rendant le code plus clair et plus testable.  
- `server.py` : gère uniquement la partie serveur MCP, l’enregistrement des outils et le logging.  
- `demo_scenario.py` : sert de preuve de fonctionnement et de test automatisé du parcours complet.

Cette architecture permet d’avoir un projet lisible, extensible et facilement maintenable.

---

## ⚙️ 3. Choix techniques principaux

### Utilisation de `uv`
Le projet utilise **uv** comme gestionnaire de dépendances et d’exécution.  
Ce choix a été fait car :
- `uv` est rapide et moderne, et recommandé par la documentation officielle de MCP.  
- Il simplifie la gestion de l’environnement virtuel et des dépendances sans avoir à utiliser `pip` ou `venv`.  
- Il permet d’exécuter directement le serveur MCP avec une commande claire :  
  `uv run mcp dev src/webpilot/server.py`  
  Et propose une interface de développement intégrée très pratique pour tester les outils et visualiser leurs résultats sans déploiement supplémentaire sur un localhost.

---

### Protocole STDIO
Le projet utilise actuellement le **mode stdio** pour la communication MCP.  
Ce mode a été choisi pour sa simplicité d’intégration :
- il ne nécessite pas de serveur HTTP externe,  
- il fonctionne parfaitement avec l’outil officiel `mcp dev`,  
- il est idéal pour les tests locaux ou la démonstration.

Cependant, le **mode SSE (Server-Sent Events)** est prévu comme évolution future.  
Ce mode permettrait une communication HTTP persistante, mieux adaptée à une mise en production ou à une intégration cloud.

---

### API Asynchrone
L’ensemble du projet repose sur l’API **asynchrone** de Playwright (`async_playwright`).  
Ce choix était nécessaire car FastMCP s’exécute déjà sur une boucle asynchrone (`asyncio`), ce qui provoquait des erreurs avec l’API synchrone.  
L’approche asynchrone présente plusieurs avantages :
- compatibilité totale avec FastMCP,  
- meilleure performance (aucun blocage de la boucle d’événements),  
- exécution fluide de plusieurs actions successives.  

Toutes les fonctions du serveur et des outils sont donc définies avec `async def` et utilisent `await` pour chaque opération Playwright (navigation, clic, capture, etc.).

---

## 🧠 4. Décisions d’implémentation dans le code

### Séparation des outils dans `tools.py`
Chaque outil (navigate, click, fill, screenshot, extract_links, get_html) a été isolé dans le fichier `tools.py`.  
Cette séparation permet :
- d’avoir un code plus modulaire,  
- de faciliter la lecture et la maintenance,  
- et de rendre le projet plus facilement testable.

Chaque fonction suit les mêmes principes :
- **Bloc `try/except`** : pour capturer les erreurs et éviter qu’une exception ne bloque tout le serveur.  
- **Retour structuré** : les fonctions renvoient un dictionnaire avec toujours les mêmes clés (`ok`, `tool`, `error`, `details`, etc.), ce qui rend les résultats faciles à interpréter.  
- **Appels asynchrones** : chaque action Playwright est précédée de `await`, afin de respecter la logique non bloquante du serveur.

---

### Choix d’implémentation de `click`
L’outil `click` a été conçu pour gérer deux cas possibles :
1. Le clic provoque une navigation (par exemple un lien).  
2. Le clic agit sur la page sans navigation (par exemple un bouton JS).  

Pour cela, la fonction essaie d’abord :
- d’attendre une navigation via `page.expect_navigation`,  
- et, en cas d’échec, exécute un simple `await page.click(selector)` sans lever d’erreur.

Ce comportement rend la fonction robuste et adaptée à la majorité des cas réels.

---

### Logging
Les journaux sont gérés avec le module `logging`.  
Chaque appel d’outil génère un log (succès ou erreur) envoyé vers **`stderr`** afin de :
- ne pas polluer les sorties JSON envoyées par MCP sur `stdout`,  
- conserver une trace claire de ce qui se passe côté serveur.  

Cela permet de distinguer les retours “machine” des retours “humains”.

---

## 🧱 5. Difficultés rencontrées et solutions

| Problème | Solution |
|-----------|-----------|
| Erreur “Playwright Sync API inside asyncio loop” | Passage complet à `async_playwright` et réécriture des outils avec `await`. |
| Problèmes de structure avec le packaging `uv` | Réorganisation du code dans `src/webpilot` et création du `pyproject.toml`. |
| Multiplication d’instances du navigateur | Mise en place d’un singleton global dans `server.py` pour réutiliser le même onglet. |

---

## 🚀 6. Améliorations prévues

- **Ajout du mode SSE (HTTP)** : permettre d’utiliser le serveur via une API web, plus pratique pour une intégration cloud.  
- **Multi-onglets / multi-sessions** : autoriser plusieurs contextes simultanés.  
- **Déploiement Cloud** : Docker + AWS ou GCP (Cloud Run, Lambda).  
- **Tests automatisés** : ajouter des tests unitaires pour chaque outil.  
- **Intégration IA avancée** : connecter les outils à LangChain, LlamaIndex ou OpenAI Functions.  
- **Interface web simple** : pour visualiser les captures et le HTML directement depuis le navigateur.

---






J'ajoute au fur et a mesur : 
probleme quand on clique sur qqch de pas visible, on le gere bien dans tools.py mais du coup leve une erreur et le serveur accepte pas le serreurs et plante. Donc on ajoute des try partout.
on a parfois plusieurs meme boutons pour mobile et pour ordi donc ajout du first dans click et fill
ajout du agent et agent.py, on décide de faire sans llm au debut pour tester facilement


**Auteur :** Hippolyte Dupont  
**Date :** Novembre 2025# DECISIONS.md
