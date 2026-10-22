# Plan — client LLM Gemini (`api/llm/clients.py`)

Statut : réalisé. Validé d'abord avec `gemini-3.1-flash-lite`, puis **passé à `gemini-3.5-flash-lite`** à la demande de l'utilisateur, car le 3.1 était trop souvent saturé (erreurs 503). Appel test réussi le 22/10/2026 sur le 3.5 : réponse « OK », 6 tokens en entrée, 0 en réflexion, 1 en sortie.

Le plan précédent (endpoint `/health`) est terminé et commité (`1e627b6`).

## 1. Choix du modèle

Le modèle doit être le moins coûteux en tokens. Sources : pages officielles Gemini API « Pricing » et « Models », consultées le 22/10/2026. Prix payants par million de tokens :

| Modèle | ID | Entrée | Sortie | Disponibilité |
|---|---|---|---|---|
| Gemini 2.5 Flash-Lite | `gemini-2.5-flash-lite` | 0,10 $ | 0,40 $ | Réservé aux comptes qui l'utilisaient déjà, déconseillé pour un nouveau projet |
| **Gemini 3.1 Flash-Lite** | `gemini-3.1-flash-lite` | **0,25 $** | **1,50 $** | **Stable, ouvert à tous, offre gratuite** |
| Gemini 3.5 Flash-Lite | `gemini-3.5-flash-lite` | 0,30 $ | 2,50 $ | Stable, offre gratuite |

**Proposition : `gemini-3.1-flash-lite`.** C'est le modèle le moins cher accessible à un nouveau projet.

- **Température :** d'après la doc, les modèles Gemini 3.6 et suivants ignorent `temperature`. Ce n'est pas le cas des Flash-Lite 3.1 et 3.5, donc la température de **0.1** sera bien appliquée.
- **Réflexion (« thinking ») :** les modèles Gemini 3 consomment des tokens de sortie pour réfléchir avant de répondre. Pour limiter la consommation, la réflexion sera réglée au niveau le plus bas accepté par le modèle (`minimal`, sinon `low`), à vérifier par un appel test.

**Point à trancher :** si ta clé a encore accès à `gemini-2.5-flash-lite`, il est environ 4 fois moins cher. Je peux le tester avec un seul appel avant de choisir.

## 2. Dépendance

Depuis `api/`, lancer :

```bash
uv add google-genai
```

C'est le SDK officiel de Google, version 2.32.0 au 22/10/2026.

## 3. Fichier `api/llm/clients.py`

Le principe : **une fonction par fournisseur, toutes avec la même signature**, pour que les routes (`/triage`, `/chat`, `/summarize`) puissent changer de fournisseur sans modifier leur code.

```python
def gemini(prompt: str, system: str | None = None) -> str:
    """Envoie le prompt à Gemini et renvoie la réponse texte."""
```

- Les constantes sont en haut du fichier : `GEMINI_MODEL = "gemini-3.1-flash-lite"` et `TEMPERATURE = 0.1`.
- La clé est lue depuis la variable d'environnement `GEMINI_API_KEY`, chargée depuis le `.env` racine, et passée explicitement au client. Le SDK lit aussi `GOOGLE_API_KEY`, qui serait prioritaire si elle existait sur la machine. Passer la clé explicitement évite toute confusion.
- Le client Gemini est créé une seule fois, au premier appel, puis réutilisé.
- Si `GEMINI_API_KEY` est absente, une erreur claire est levée, sans jamais afficher de valeur de clé.
- Le fournisseur local (Ollama ou autre) viendra plus tard, sous la forme d'une deuxième fonction avec la même signature, par exemple `local(prompt, system)`.

Aucune route n'est modifiée à cette étape.

## 4. Vérification

- Faire un seul appel test très court (« Réponds uniquement : OK ») via `uv run`, en chargeant le `.env` racine. Contrôler que la réponse arrive et que le niveau de réflexion choisi est accepté.
- Afficher le nombre de tokens consommés (entrée, réflexion, sortie) renvoyé par l'API, pour confirmer que la consommation est minimale.
- La valeur de la clé ne doit apparaître nulle part dans les logs ni dans la sortie.

## Ajout : prompt système SOC commun (22/10/2026, réalisé)

À la demande de l'utilisateur, tous les appels LLM appliquent désormais les mêmes règles, définies dans `api/llm/prompts.py` en 4 blocs : rôle, contexte, contraintes et format de sortie. `clients.py` les ajoute à chaque appel, et le paramètre `system` ne fait qu'ajouter des instructions à la suite.

Les tests sur deux alertes ont fait apparaître deux défauts de la version mot pour mot du cours :
- le modèle recopiait la ligne de format ;
- il inventait des détails absents de l'alerte.

Corrections apportées : le format est donné sous forme de modèle à remplir, et la règle « incertitude » est renforcée. Résultat :
- l'alerte SSH root est classée HIGH, avec 3 actions ;
- l'alerte svchost, trop vague, renvoie « incertitude » en précisant les informations manquantes.

## Ajout : modèle local phi4-mini et playground (22/10/2026, réalisé)

- **Installation :** Ollama 0.40.8 et le modèle `phi4-mini` téléchargé avec `ollama pull`.
- **Client local :** `clients.ollama()` appelle l'API Ollama `/api/chat` avec la même signature, le même prompt SOC et la même température (0.1) que Gemini. Le registre `PROVIDERS` associe `gemini` et `phi4` à leur fonction.
- **Playground :** une page de chat sur `/playground`, avec bascule entre `gemini` et `phi4`, s'appuie sur l'endpoint `POST /playground/ask`.
- **Tests :** l'alerte SSH root est classée HIGH par les deux fournisseurs, avec le format respecté. Durées : phi4 11 s, Gemini 8 s. L'interface a été testée dans le navigateur avec phi4 (réponse en 9 s). Un fournisseur inconnu renvoie 400.

## 5. Finaliser

- Mettre à jour `CLAUDE.md` : modèle, température, rôle de `llm/clients.py` et nouvelle dépendance.
- Pas de commit automatique : il sera proposé à la fin.
