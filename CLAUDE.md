# assistant-soc

Assistant IA pour un SOC (Security Operations Center), réalisé dans le cadre du cours Formatik « Développement Solution IA » (formateur : Fabrice).

- Dépôt GitHub **public** : https://github.com/gruy22/assistant-soc (branche `main`)
- Langue du projet : français (commentaires, commits, documentation)

## Architecture cible

```
assistant-soc/
├── api/                  Backend FastAPI (Python)
│   ├── main.py           application FastAPI
│   ├── routers/          endpoints /triage, /chat, /summarize
│   ├── llm/              clients LLM cloud + local
│   ├── rag/              chunking, embeddings, retrieve
│   └── pyproject.toml    dépendances gérées par uv
├── frontend/             React (jour 6)
├── data/
│   ├── tickets.json      500 tickets SOC fictifs
│   ├── runbooks/         30 runbooks Markdown
│   └── cve.json          200 CVE 2024-2026
└── terraform/            main.tf (jour 3)
```

Fonctions de l'API :
- `/triage` : trier / prioriser les tickets SOC
- `/chat` : discuter avec l'assistant (RAG sur runbooks, CVE, tickets)
- `/summarize` : résumer un ticket ou un incident

État actuel : squelette en place, le développement n'a pas commencé.
- `api/` : `main.py` et les paquets `routers/`, `llm/`, `rag/` ne contiennent qu'une docstring ; `pyproject.toml` créé par `uv init`, sans dépendance.
- `data/` : `tickets.json` et `cve.json` sont des listes vides, `runbooks/` est vide.
- `frontend/` et `terraform/` : vides (jours 6 et 3).

Le cours avance étape par étape : ne pas écrire de code ni générer de données sans demande explicite de l'utilisateur.

Commandes (depuis `api/`) : `uv add <paquet>` pour ajouter une dépendance, `uv run <commande>` pour exécuter dans l'environnement du projet.

## Stack

- **Backend** : Python 3.12, FastAPI, dépendances gérées avec `uv` (`api/pyproject.toml`)
- **LLM** : cloud (Google Gemini, clé `GEMINI_API_KEY`) + modèle local
- **RAG** : découpage, embeddings et recherche sur `data/`
- **Frontend** : React
- **Infra** : Terraform 1.16.x (fournisseur cloud : _à définir_)

## Secrets et clés API

- Toutes les clés API sont dans `.env` à la racine (actuellement : `GEMINI_API_KEY`).
- `.env` est ignoré par git. Le dépôt étant public, ne jamais commiter de secret, ne jamais écrire une clé en dur dans le code ni afficher sa valeur.
- Le code charge les clés depuis `.env` par leur nom (ex. `python-dotenv`, `process.env`).
- Si une nouvelle clé est nécessaire, demander à l'utilisateur de l'ajouter dans `.env` et documenter son nom dans un `.env.example` (sans valeur).
- `*.tfvars` et `*.tfstate` sont aussi ignorés : y mettre les valeurs sensibles Terraform, jamais dans les `.tf`.

## Environnement de développement

- Windows 11, PowerShell
- Outils installés : git, GitHub CLI (`gh`, compte `gruy22`), Terraform, Node.js/npm, Python 3.12, uv

## Conventions

- Commits en français, petits et ciblés ; pousser sur `main` sauf demande contraire.
- Mettre à jour ce fichier quand la stack, la structure ou les commandes changent.
