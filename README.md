# WFM Tactical Platform – Pilotage Prédictif & Supervision Temps Réel pour Centres d’Appels

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)](https://www.sqlalchemy.org/)
[![Render](https://img.shields.io/badge/Deploy-Render-purple?logo=render)](https://render.com)
[![Licence MIT](https://img.shields.io/badge/Licence-MIT-yellow)](LICENSE)

**Système Tactique de Pilotage Prédictif, d’Inférence Continue et d’Optimisation du Staffing pour Centres de Contact (Workforce Management)**.  
Conçu pour répondre aux besoins des opérateurs télécoms (Orange, MTN, Intelcia) avec une précision de 15 minutes, des algorithmes de prévision hybrides, et un suivi temps réel des agents.

---

## Table des matières
- [ Contexte métier](#-contexte-métier)
- [ Fonctionnalités](#-fonctionnalités)
- [ Architecture](#-architecture)
- [ Stack technique](#-stack-technique)
- [ Installation & Lancement](#️-installation--lancement)
- [ Utilisation](#️-utilisation)
- [ Endpoints API](#-endpoints-api)
- [ Structure du projet](#-structure-du-projet)
- [ Déploiement](#-déploiement)
- [ Tests](#-tests)
- [ Métriques & Algorithmes](#-métriques--algorithmes)
- [ Licence](#-licence)
- [ Contact](#-contact)

---

## Contexte métier
Les centres d’appels des opérateurs télécoms (Orange, MTN, Intelcia) doivent **prévoir le volume d’appels**, **dimensionner leurs équipes** et **réagir en temps réel** aux variations de charge (crises réseau, sous‑effectif, etc.).  
Ce projet simule un environnement de production complet avec :

- **Pas de temps tactique** : 15 minutes (96 intervalles/jour)
- **AHT** (Average Handling Time) : plafonné à **420 secondes**
- **Taux de shrinkage** : 17,65% (pauses, formations)
- **SLA** : 80% des appels répondus en moins de 20 secondes (Erlang‑C)

La plateforme combine **supervision live**, **aide à la décision** et **planification à J+7**, le tout dans une interface **Glassmorphism Néon** moderne.

---

## Fonctionnalités
### Supervision en temps réel (rafraîchie toutes les 30 secondes)
- **8 cartes KPI** (Longest Waiting, Current Waiting, Average Talk Time, Total Calls, Agent Ready, Agent Logged In, ASA, Abandoned)
- **Statuts détaillés des agents** : présents, en pause 15 min / 1 h (avec compte à rebours), appels > 420 s, retards, shifts terminés
- **Graphique Spline** (appels actifs vs en attente) avec zone remplie et échelle 0‑100
- **Jauge d’activité** semi‑circulaire avec gradient néon
- **Bloc Service Level** avec occupation et alertes (sous/sur‑occupation)

### Prévisions de flux – 24 heures
- **Graphique double axe** : volume prédit + agents nets requis (toutes les 15 minutes)
- **Recalculées toutes les 10 minutes** (ou automatiquement via le scheduler)

### Planification hebdomadaire (J+7)
- **Tableau journalier** : volume total d’appels, agents nets/bruts au pic, SLA cible
- **Calcul basé sur l’Erlang‑C** appliqué aux prévisions simulées (SARIMA + XGBoost simulé)

### Simulation de scénarios
- **Boutons de crise** : Standard, Crise réseau, Sous‑effectif
- **Injection de données** : chaque scénario injecte 2 intervalles (30 min) dans la base
- **Rafraîchissement automatique** du dashboard après injection

### Planification automatique
- **Scheduler intégré** (APScheduler) pour les prévisions et l’injection de données toutes les 30 minutes
- **Démarrage immédiat** avec un historique complet depuis minuit

---

## Architecture
Le projet suit une **architecture modulaire en couches** avec une séparation claire des responsabilités :

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Static)               │
│  HTML5 / CSS3 / Vanilla JS + Chart.js            │
│  Thème Glassmorphism Néon                        │
└────────────────┬────────────────────────────────┘
                 │ API REST (FastAPI)
┌────────────────┴────────────────────────────────┐
│                Backend (Python 3.11+)             │
│  ┌─────────────────────────────────────────────┐ │
│  │            Services métier                   │ │
│  │  • Erlang‑C (staffing)                      │ │
│  │  • Simulateur (SARIMA+XGBoost)              │ │
│  │  • Générateur de flux (scénarios)           │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │            Modèles (SQLAlchemy 2.0)          │ │
│  │  • historical_flux                           │ │
│  │  • predictions_tactical                     │ │
│  │  • agent_staffing                            │ │
│  │  • model_metrics                             │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │            Scheduler (APScheduler)           │ │
│  │  • Prévisions toutes les 30 min              │ │
│  │  • Injection données toutes les 30 min       │ │
│  └─────────────────────────────────────────────┘ │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────┐
│           Base de données (SQLite / PostgreSQL)   │
└─────────────────────────────────────────────────┘
```

---

## 📦 Stack technique
| Composant            | Technologie                         | Version        |
|----------------------|-------------------------------------|----------------|
| Backend              | Python + FastAPI                    | 3.8+ / 0.111.0 |
| ORM                  | SQLAlchemy 2.0 (async)              | 2.0.30         |
| Base de données      | SQLite (dev) / PostgreSQL (prod)    | –              |
| Planification        | APScheduler                         | 3.10.4         |
| Frontend             | HTML5, CSS3, Vanilla JS             | –              |
| Graphiques           | Chart.js                            | 4.4.1          |
| Tests                | Pytest + asyncio                    | 8.2.2          |
| Conteneurisation     | Docker (multi‑stage)                | –              |
| CI/CD                | GitHub Actions                      | –              |
| Déploiement          | Render (Blueprint)                  | –              |

---

## ⚙️ Installation & Lancement

### Prérequis
- Python 3.8 ou supérieur (3.11 recommandé)
- pip
- (optionnel) PostgreSQL pour la production

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-utilisateur/wfm-tactical-platform.git
cd wfm-tactical-platform
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configuration (optionnelle pour le dev local)
Un fichier `.env` peut être créé pour surcharger les paramètres :
```env
ENV=dev
DATABASE_URL=sqlite+aiosqlite:///./wfm.db
LOG_LEVEL=INFO
```
Par défaut, l’application utilise **SQLite** et crée un fichier `wfm.db` à la racine.

### 5. Lancer le serveur
```bash
uvicorn app.main:app --reload
```
Ouvrir [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html) dans le navigateur.

---

## Utilisation
Une fois l’application démarrée, le dashboard affiche immédiatement des données simulées (historique depuis minuit + prévisions).  
- **Supervision live** : les KPI et graphiques se rafraîchissent toutes les 30 secondes.
- **Scénarios** : cliquez sur les boutons de crise (Crise réseau, Sous‑effectif) pour injecter des données immédiatement visibles.
- **Prévisions 24h** : courbes de volume et staffing sur la journée en cours.
- **Planification hebdomadaire** : tableau récapitulatif pour les 7 prochains jours.

---

## Endpoints API
| Méthode | Endpoint                        | Description                                   |
|---------|---------------------------------|-----------------------------------------------|
| GET     | `/api/v1/live/kpis`            | KPIs temps réel (8 métriques)                 |
| GET     | `/api/v1/live/agents`          | Statut des agents (pauses, retards, etc.)     |
| GET     | `/api/v1/live/series`          | Séries temporelles (active/on hold) 60 min    |
| GET     | `/api/v1/predict/today`        | Prévisions 15 min pour la journée             |
| GET     | `/api/v1/predict/week`         | Planification journalière sur 7 jours         |
| POST    | `/api/v1/simulation/trigger`   | Injection de scénarios (standard, crise, etc.)|

Des exemples de réponses sont disponibles dans la documentation interactive Swagger :  
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## Structure du projet
```
workforce/
├── app/
│   ├── core/                 # Configuration & logging
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── models/               # Modèles SQLAlchemy + DB
│   │   ├── base.py
│   │   ├── database.py
│   │   └── domain.py
│   ├── services/             # Logique métier
│   │   ├── erlang_c.py       # Formule Erlang-C
│   │   ├── forecaster.py     # Prévisions simulées
│   │   └── simulator.py      # Générateur de flux
│   └── main.py               # Application FastAPI & routes
├── static/                   # Frontend (Glassmorphism)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── scripts/
│   └── eda_generate_historical.py
├── tests/                    # Tests unitaires & intégration
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_crud.py
│   ├── test_erlang_c.py
│   └── test_forecaster.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── render.yaml
└── .github/workflows/deploy.yml
```

---

## Déploiement

### Render (gratuit)
Le projet est prêt pour un déploiement sur Render avec son **Blueprint** (`render.yaml`).  
1. Connectez votre dépôt GitHub à Render.
2. Le service `wfm-tactical-platform` et la base PostgreSQL `wfm-db` seront créés automatiquement.
3. Définissez le secret `RENDER_DEPLOY_HOOK` dans votre repo GitHub pour le déploiement continu.

### Docker
Construction et exécution locale :
```bash
docker build -t wfm-platform .
docker run -p 8000:8000 wfm-platform
```

### GitHub Actions
Le pipeline CI/CD (`.github/workflows/deploy.yml`) exécute automatiquement à chaque push sur `main` :
- Linting (flake8, black)
- Tests unitaires (pytest)
- Déploiement sur Render via webhook

---

## Tests
Exécutez la suite de tests avec :
```bash
python -m pytest tests/ -v
```
Tous les tests utilisent une base SQLite en mémoire, aucune dépendance externe n’est requise.  
**20 tests** couvrent :
- CRUD des modèles
- Calculs Erlang‑C (probabilités, staffing, SLA)
- Prévisions (nombre d’intervalles, métriques)
- API (endpoints live, simulation, dashboard)

---

## Métriques & Algorithmes
### Erlang‑C
La formule d’Erlang‑C calcule la probabilité d’attente et le nombre d’agents nécessaires pour atteindre le SLA.  
Implémentation pure Python, sans librairie externe.

### Prévisions
Un modèle **SARIMA simulé** capture la saisonnalité quotidienne/hebdomadaire, corrigé par un **XGBoost simulé** pour les événements exogènes (crises réseau).  
Les prévisions sont générées toutes les 30 minutes et stockées en base.

### Indicateurs clés
| Métrique              | Formule / Plafond               |
|-----------------------|---------------------------------|
| AHT max               | 420 secondes (7 min)            |
| Shrinkage             | 17.65%                          |
| Staffing Net          | Staffing Brut / (1 - 0.1765)    |
| SLA cible             | 80% des appels répondus en <20s |
| Occupation critique   | <65% (sous‑occupation), >85% (sur‑occupation) |

---

## Licence
Ce projet est sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## Contact
**David Mechant** – Étudiant en Data Science / DevOps / MLOps / IA  
- GitHub : [votre-utilisateur](https://github.com/monsieurMechant200)
- LinkedIn : [votre-profil](https://linkedin.com/in/david-meilleur-aat-ndongo-bb43b0314)

Ce projet a été réalisé dans le cadre d’un **portfolio de niveau Sciences de l'Ingénieur** pour décrocher un stage chez **Orange, MTN ou Intelcia**.
