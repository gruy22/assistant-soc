"""Clients LLM : une fonction par fournisseur, toutes avec la même signature.

    fournisseur(prompt: str, system: str | None = None) -> str

Les routes peuvent ainsi changer de fournisseur sans modifier leur code.
Le prompt système SOC commun (llm/prompts.py) est toujours appliqué ; `system` ajoute
des instructions propres à l'appel, à la suite de ces règles.
Les clés API sont lues dans les variables d'environnement (chargées depuis le .env racine).
"""

import os
from collections.abc import Callable

import httpx
from google import genai
from google.genai import types

from llm.prompts import SOC_SYSTEM_PROMPT

# Flash-Lite 3.5 : 3.1 trop souvent saturé (erreurs 503). Les modèles >= 3.6 ignorent la température.
GEMINI_MODEL = "gemini-3.5-flash-lite"
TEMPERATURE = 0.1
# Réflexion au minimum pour limiter les tokens de sortie
GEMINI_THINKING_LEVEL = types.ThinkingLevel.MINIMAL

# Modèle local servi par Ollama (télécharger avec : ollama pull phi4-mini)
OLLAMA_MODEL = "phi4-mini"
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
# Exécution locale, parfois lente sur CPU
OLLAMA_TIMEOUT_S = 300
# Sous Windows, Ollama renvoie parfois 500 alors que la génération a réussi
# (« health resp: ... wsarecv: An existing connection was forcibly closed ») : on réessaie.
OLLAMA_ATTEMPTS = 2

_gemini_client: genai.Client | None = None


def _get_gemini_client() -> genai.Client:
    """Crée le client Gemini au premier appel, puis le réutilise."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY absente : l'ajouter dans le .env à la racine du projet.")
        # Clé passée explicitement : le SDK donnerait sinon la priorité à GOOGLE_API_KEY
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _build_system(system: str | None) -> str:
    """Règles SOC communes, suivies des instructions propres à l'appel s'il y en a."""
    if not system:
        return SOC_SYSTEM_PROMPT
    return f"{SOC_SYSTEM_PROMPT}\n# Instructions supplémentaires\n{system}"


def gemini(prompt: str, system: str | None = None) -> str:
    """Envoie le prompt à Gemini et renvoie la réponse texte."""
    response = _get_gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_build_system(system),
            temperature=TEMPERATURE,
            thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL),
        ),
    )
    return response.text or ""


def ollama(prompt: str, system: str | None = None) -> str:
    """Envoie le prompt au modèle local (Ollama) et renvoie la réponse texte."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _build_system(system)},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    for attempt in range(1, OLLAMA_ATTEMPTS + 1):
        response = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_S)
        if response.status_code < 500 or attempt == OLLAMA_ATTEMPTS:
            break
    if response.is_error:
        raise RuntimeError(f"Ollama a répondu {response.status_code} : {_ollama_error(response)}")
    return response.json()["message"]["content"]


def _ollama_error(response: httpx.Response) -> str:
    """Message d'erreur renvoyé par Ollama (champ « error » du JSON), sinon le texte brut."""
    try:
        return response.json()["error"]
    except (ValueError, KeyError, TypeError):
        return response.text or response.reason_phrase


# Fournisseurs disponibles : nom -> (fonction, modèle)
PROVIDERS: dict[str, tuple[Callable[[str, str | None], str], str]] = {
    "gemini": (gemini, GEMINI_MODEL),
    "phi4": (ollama, OLLAMA_MODEL),
}
