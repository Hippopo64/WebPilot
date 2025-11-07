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


# Architecture Cloud Azure – Présentation & Justification

Cette architecture a été conçue pour respecter trois consignes :

-   **Un SLA de 99.9%**,
    
-   **Une scalabilité jusqu’à 1000 utilisateurs en même temps**,
    
-   **Une conformité stricte (RGPD, ISO 27001, audit mensuel, traçabilité)**.
    

Elle repose sur un modèle de **microservices** déployés dans **Azure Kubernetes Service (AKS)** et protégés par une **isolation réseau via Azure Virtual Network (VNet)**.

# Services Azure utilisés
-   **Azure Front Door**

-   **Azure API Management (APIM)**

-   **Azure Application Gateway (WAF)**

-   **Azure Virtual Network (VNet)**

-   **Azure Kubernetes Service (AKS)**

-   **Azure Firewall + IP Pool**

-   **Azure Cache for Redis**

-   **Azure PostgreSQL**

-   **Azure Blob Storage**

-   **Azure Key Vault**

-   **Azure Service Bus**

-   **Azure Monitor + Log Analytics**

-   **Microsoft Sentinel**


# 1. Vue d’ensemble du flux utilisateur

Le parcours d’une requête dans WebPilot suit un flux en plusieurs couches, chacun ayant un rôle de sécurité ou de performance.

### **1) Entrée utilisateur**

**Azure Front Door** est le point d’entrée global.  
Il s'assure de la répartition du trafic, de la disponibilité du service et d'une reprise facile en cas de panne.

### **2) Vérification & conformité**

**Azure API Management (APIM)** applique les règles importantes, comme l'authentification, la limitation du débit, la lecture du _robots.txt_ pour vérifier si l'on est autorisé à aller sur ce site web.

### **3) Protection anti-attaques**

**Application Gateway équipée du WAF** filtre les requêtes HTTP et bloque les attaques. 

### **4) Réseau privé**

**Azure Virtual Network (VNet)** contient tous les composants sensibles pour les isoler dans un réseau privé.


----------

# 2. Exécution du scraping & de l’IA – Azure Kubernetes Service (AKS)

**AKS** héberge les 3 micro-services du projet :

- **WebPilot (Playwright)** ouvre les pages, clique, scroll, extrait le HTML, etc... Il fait toutes les actions d'un utilisateurs sur un navigateur
- **Selector-LLM Service** analyse le HTML via un appel à un LLM et renvoie les sélecteurs correspondants à la demande

- **LiteLLM Proxy** gère les appels vers Groq en utilisant la clé API, et en gérant le cache, les limites, les coûts, etc...


AKS est l’endroit où se passe réellement le script du projet. De plus il permet un auto-scaling pour gérer les pics d'utilisateurs.

----------

# 3. Services internes au VNet : Performance & Données

- **Azure Cache for Redis** est un cache partagé qui stocke robots.txt, les réponses LLM, le HTML, etc... Afin de réduire la latence 
- **Azure PostgreSQL** est une Base de Données qui sauvegarde l'historique, les utilisateurs, les metadonnées, etc... Toutes les informations utiles dans le temps.
- **Azure Blob Storage** stocke les fichiers lourds comme le HTML, les captures d'écran, les fichiers, etc...

- **Azure Key Vault** protège les fichiers et données sensibles comme la clé API, les certificats, et les clés de chiffrement

Ces services sont accessibles uniquement via des Private Endpoints.

----------

# 4. Sortie Internet contrôlée – Azure Firewall + Rotation d’IP

Pour respecter les politiques strictes sur le scraping, le navigateur _Playwright_ est le seul composant autorisé à sortir du **VNet**. Et il ne peut sortir que via **Azure Firewall**. Le firewall permet de filtrer les domaines autorisés, changer d'IP via un pool et surtout d'avoir une vue d'ensemble des sorties. Cela permet finalement d'éviter des blocages.

----------

# 5. Gestion des pics de charge – Azure Service Bus

Si il y a beaucoup de requêtes (le pic de 1000 utilisateurs), **Azure Service Bus** propose une file d'attente. Les requêtes sont mises dans une queue. Ensuite les micro-services les gèrent une par une.

----------

# 6. Observabilité & Audit – Azure Monitor + Sentinel

- **Azure Monitor + Log Analytics** centralise les logs de tous les outils comme l'APIM, le AKS, le Firewall, etc...
- **Microsoft Sentinel** analyse les logs de Monitor et tente de détecter les anomalies, lève des alertes, automatise des rapports de conformité (ISO 27001 et RGPD).

----------

# Résumé 

Cette architecture prpose de la sécurité, de la performance et respecte les conformités.  
Le trafic est filtré et validé dès l’entrée (Front Door, APIM, WAF) avant d’être isolé dans un réseau privé (VNet).  
L’exécution du scraping et du traitement IA se déroule dans AKS, qui est capable de s’adapter automatiquement à la surcharge d'utilisateurs via l’auto-scaling.  
Les données sont stockées dans des services sécurisés (Redis, PostgreSQL, Blob) accessibles via Private Endpoints, et les sorties Internet sont contrôlées par le firewall.  
Puis, le tout est contrôlé par Monitor et Sentinel qui offrent une traçabilité complète et un respect des normes RGPD et ISO 27001.

📦 Licence

MIT – usage démonstratif et éducatif.
