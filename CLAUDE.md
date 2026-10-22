# assistant-soc

Assistant IA pour un SOC (Security Operations Center), réalisé dans le cadre du cours Formatik « Développement Solution IA » (formateur : Fabrice).

- Dépôt GitHub **public** : https://github.com/gruy22/assistant-soc (branche `main`)
- Langue du projet : français (commentaires, commits, documentation)

## Structure

| Dossier | Rôle |
|---|---|
| `api/` | Backend / API de l'assistant |
| `frontend/` | Interface utilisateur |
| `data/` | Données utilisées par l'assistant (jeux de données, logs, documents) |
| `terraform/` | Infrastructure as Code pour le déploiement |

Les dossiers ne contiennent pour l'instant qu'un `.gitkeep` : le code reste à écrire.

## Stack

- **LLM** : Google Gemini (clé `GEMINI_API_KEY`)
- **Infra** : Terraform 1.16.x
- Backend, frontend, fournisseur cloud : _à définir_

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
