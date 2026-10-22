# Plan — initialisation de l'API et endpoint `/health`

Statut : **validé avec l'option B** (le `.env` reste à la racine) et réalisé. `.env.example` est donc à la racine.

## 1. Compléter le projet Python dans `api/`

- `api/pyproject.toml` existe déjà (créé par `uv init`).
- Depuis `api/`, lancer :
  ```bash
  uv add fastapi "uvicorn[standard]" python-dotenv
  ```
- uv crée l'environnement virtuel `api/.venv` (ignoré par git) et `api/uv.lock` (à commiter).
- « python-env » est interprété comme **python-dotenv**, le paquet qui lit les fichiers `.env`.
- `uvicorn[standard]` ajoute de quoi détecter efficacement les modifications pour le rechargement automatique.

## 2. Charger les variables depuis `api/.env`

- Dans `api/main.py`, appeler `load_dotenv()` en pointant explicitement sur `api/.env`, quel que soit le dossier d'où le serveur est lancé.
- Créer `api/.env.example` avec seulement le nom des variables, sans valeur :
  ```
  GEMINI_API_KEY=
  ```
- Le `.gitignore` exclut déjà les `.env` dans tous les sous-dossiers : `api/.env` ne partira pas sur GitHub.

**Point à trancher :** le `.env` actuel est à la racine du projet.
- **Option A (proposée)** : le déplacer dans `api/.env`, sans l'ouvrir.
- **Option B** : le laisser à la racine et faire lire ce fichier par `api/`.

## 3. Endpoint `/health`

- Dans `api/main.py` : créer l'application FastAPI et une route `GET /health` qui renvoie :
  ```json
  {"status": "ok"}
  ```
- `routers/` reste réservé à `/triage`, `/chat` et `/summarize`.

## 4. Lancer le serveur

- Dans un onglet du terminal, depuis `api/` :
  ```bash
  uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
  ```
- Les logs restent visibles dans l'onglet, arrêt avec Ctrl+C.

## 5. Agent de test

Une fois le serveur démarré, un agent séparé vérifie :
- `GET http://localhost:8000/health` répond avec le code HTTP **200** ;
- le corps de la réponse est exactement `{"status": "ok"}` ;
- le rechargement à chaud fonctionne : modification temporaire du code, constat du rechargement, puis remise du fichier dans son état d'origine.

L'agent renvoie un rapport, qui est transmis à l'utilisateur.

## 6. Finaliser

- Mettre à jour `CLAUDE.md` : état du projet et commande de lancement.
- Pas de commit automatique : il sera proposé à la fin.
