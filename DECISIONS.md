
---

## DECISIONS.md – version détaillée et professionnelle

```markdown
# 📘 DECISIONS.md

Ce document décrit les **choix techniques**, **compromis** et **enseignements** liés au développement du projet *WebPilot MCP*.

---

## 🎯 Objectif du projet

Créer un **serveur MCP (Model Context Protocol)** exposant des outils d’automatisation web simples mais représentatifs.  
L’idée : permettre à un modèle d’intelligence artificielle d’interagir avec des pages web de manière contrôlée et reproductible (ouvrir une page, extraire des liens, cliquer, remplir un champ, etc.).

---

## ⚙️ Architecture et choix principaux

### 🧩 Utilisation de **FastMCP SDK**
- Choisi pour sa compatibilité native avec les clients MCP modernes (OpenAI, Anthropic, etc.).
- Permet d’enregistrer facilement des outils via des décorateurs `@mcp.tool()`.
- Évite d’avoir à gérer un serveur HTTP complet (FastAPI/Flask) et se concentre sur la communication IA ↔ outils.

### ⚙️ API **asynchrone**
- FastMCP repose sur **asyncio**, il fallait donc utiliser **Playwright.async_api** pour éviter les blocages.
- Cela permet d’exécuter plusieurs actions sans bloquer la boucle d’événements.
- Corrige l’erreur classique : “Playwright Sync API inside asyncio loop”.

### 🌐 Navigateur partagé (pattern singleton)
- Un seul navigateur et un seul onglet ouverts pour tous les outils.
- Gain de performance et réduction de consommation mémoire.
- Centralisé dans `browser.py` via des variables globales (`_P`, `_B`, `_PAGE`).

### 📦 Format de réponse JSON standardisé
Tous les outils suivent le même schéma :
```json
{ "ok": true, "tool": "navigate", "url": "...", "status": 200 }
