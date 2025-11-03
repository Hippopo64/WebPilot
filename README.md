# 🧠 WebPilot MCP – Automatisation de navigateur via IA

Ce projet a été réalisé dans le cadre du test technique pour le poste de **Développeur Full-Stack IA** chez **TW3 Partners**.  
Il illustre un petit **serveur MCP (Model Context Protocol)** exposant des outils d’automatisation de navigateur à l’aide de **Playwright**.  
Ces outils permettent à un modèle (ou à un agent IA) de naviguer sur le web, d’extraire des liens, de remplir des formulaires, de cliquer sur des éléments et de prendre des captures d’écran.

---

## 🚀 Fonctionnalités principales

| Outil | Description |
|--------|-------------|
| `navigate(url)` | Ouvre une URL dans le navigateur partagé. |
| `screenshot(path, full)` | Prend une capture d’écran (fenêtre ou page complète). |
| `extract_links(contains)` | Extrait tous les liens présents sur la page. |
| `fill(selector, text)` | Remplit un champ de formulaire identifié par un sélecteur CSS. |
| `click(selector)` | Clique sur un élément cliquable. |
| `get_html(save_path)` | Récupère le HTML rendu, avec option d’enregistrement. |

Tous les outils renvoient des réponses **JSON structurées** (`ok`, `error`, `details`, etc.) et journalisent leurs actions via `logging`.

---

## 🧩 Architecture du projet

src/
└── webpilot/
├── browser.py # Gestion du navigateur Playwright (async singleton)
├── tools.py # Définition des outils exposés
├── server.py # Serveur MCP FastMCP exposant les tools
└── demos/
└── demo_scenario.py # Scénario de démonstration automatisé


- Le serveur utilise **FastMCP SDK** pour exposer les outils via le protocole **MCP (stdio)**.  
- Le navigateur est partagé entre les outils pour éviter les redémarrages coûteux.  
- Les logs sont envoyés vers `stderr` pour une observation simple et claire.

---

## ⚙️ Installation et exécution

### 1. Installer les dépendances
```bash
uv sync

2. Installer le navigateur Playwright
uv run playwright install chromium

3. Lancer le serveur en mode développement (inspecteur MCP)
uv run mcp dev src/webpilot/server.py

4. Lancer la démonstration automatique
uv run python -m webpilot.demos.demo_scenario


Les fichiers générés se trouvent dans demo_outputs/ :

00_example_viewport.png

01_external_full.png

01_external.html

🧪 Exemple de déroulement

navigate → https://example.com

screenshot → example_viewport.png

extract_links

navigate vers le premier lien externe

screenshot → external_full.png

🧱 Stack technique

Python 3.10+

Playwright (API asynchrone)

Model Context Protocol (FastMCP SDK)

uv (gestionnaire de dépendances)

logging (suivi des actions)

📦 Licence

MIT – usage démonstratif et éducatif.