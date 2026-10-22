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

État actuel :
- `api/main.py` : application FastAPI, charge le `.env` de la racine (`python-dotenv`), expose `GET /health` → `{"status": "ok"}` et inclut le router `playground`.
- `api/pyproject.toml` / `uv.lock` : dépendances `fastapi`, `uvicorn[standard]`, `python-dotenv`, `google-genai`, `httpx`.
- `api/llm/clients.py` : une fonction par fournisseur LLM, toutes avec la signature `fournisseur(prompt: str, system: str | None = None) -> str`, température 0.1 pour toutes.
  - `gemini()` : modèle `gemini-3.5-flash-lite` (le 3.1 Flash-Lite, moins cher, était trop souvent saturé ; la température est prise en compte jusqu'aux modèles 3.5 et ignorée à partir de 3.6 ; réflexion `MINIMAL`).
  - `ollama()` : modèle local `phi4-mini` via l'API Ollama (`POST /api/chat`, `http://127.0.0.1:11434`, surchargeable par la variable `OLLAMA_HOST`), appelée avec `httpx`. Sous Windows, Ollama renvoie parfois 500 alors que la génération a réussi (« health resp: … wsarecv ») : `ollama()` réessaie une fois sur les erreurs 5xx, puis lève une `RuntimeError` avec le vrai message d'Ollama (champ `error`).
  - `PROVIDERS` : registre `nom -> (fonction, modèle)` (`gemini`, `phi4`) ; ajouter un fournisseur ici le rend disponible dans le playground.
- `api/routers/playground.py` + `api/static/playground.html` : interface de test type chat, sur http://127.0.0.1:8000/playground, avec bascule entre fournisseurs. Endpoints : `GET /playground/providers`, `POST /playground/ask` `{provider, prompt}` → `{provider, model, answer, duration_s}`. Chaque message est traité seul, sans mémoire de conversation.
- `api/llm/prompts.py` : `SOC_SYSTEM_PROMPT`, règles communes à **tous** les utilisateurs et tous les appels LLM (rôle analyste SOC L2, contexte PME 500 postes AD + Linux / équipe de 2, réponses en français, 3 actions max, « incertitude » plutôt qu'inventer, format Sévérité HIGH/MEDIUM/LOW + Explication 2 phrases + Actions numérotées). Chaque fonction de `clients.py` l'applique toujours ; le paramètre `system` ne fait qu'ajouter des instructions à la suite, il ne le remplace pas.
- `routers/` : seulement `playground.py` pour l'instant ; `/triage`, `/chat`, `/summarize` restent à faire. `rag/` ne contient qu'une docstring.
- `data/` : `tickets.json` et `cve.json` sont des listes vides, `runbooks/` est vide.
- `frontend/` et `terraform/` : vides (jours 6 et 3).

Le cours avance étape par étape : ne pas écrire de code ni générer de données sans demande explicite de l'utilisateur.

Commandes (depuis `api/`) :
- Lancer l'API en local avec rechargement : `uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000` (docs : http://127.0.0.1:8000/docs, playground : http://127.0.0.1:8000/playground)
- Modèle local : `ollama pull phi4-mini` (une fois) ; Ollama doit tourner (service lancé au démarrage de Windows, port 11434)
- Ajouter une dépendance : `uv add <paquet>`
- Exécuter dans l'environnement du projet : `uv run <commande>`
- Sous Windows, arrêter uvicorn avant `uv add` / `uv sync` : le serveur verrouille des fichiers de `.venv` et l'installation échoue (« Accès refusé »).

## Stack

- **Backend** : Python 3.12, FastAPI, dépendances gérées avec `uv` (`api/pyproject.toml`)
- **LLM** : cloud (Google Gemini, clé `GEMINI_API_KEY`) + local (Ollama, `phi4-mini`)
- **RAG** : découpage, embeddings et recherche sur `data/`
- **Frontend** : React
- **Infra** : Terraform 1.16.x (fournisseur cloud : _à définir_)

## Secrets et clés API

- Toutes les clés API sont dans `.env` à la racine (actuellement : `GEMINI_API_KEY`), chargé par `api/main.py`. Les noms des variables sont listés dans `.env.example`.
- `.env` est ignoré par git. Le dépôt étant public, ne jamais commiter de secret, ne jamais écrire une clé en dur dans le code ni afficher sa valeur.
- Le code charge les clés depuis `.env` par leur nom (ex. `python-dotenv`, `process.env`).
- Si une nouvelle clé est nécessaire, demander à l'utilisateur de l'ajouter dans `.env` et documenter son nom dans un `.env.example` (sans valeur).
- `*.tfvars` et `*.tfstate` sont aussi ignorés : y mettre les valeurs sensibles Terraform, jamais dans les `.tf`.

## Environnement de développement

- Windows 11, PowerShell
- Outils installés : git, GitHub CLI (`gh`, compte `gruy22`), Terraform, Node.js/npm, Python 3.12, uv, Ollama 0.40.8

## Conventions

- Commits en français, petits et ciblés ; pousser sur `main` sauf demande contraire.
- Mettre à jour ce fichier quand la stack, la structure ou les commandes changent.
