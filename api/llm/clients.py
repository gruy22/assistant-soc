"""Clients LLM : une fonction par fournisseur, toutes avec la même signature.

    fournisseur(prompt: str, system: str | None = None) -> str

Les routes peuvent ainsi changer de fournisseur sans modifier leur code.
Les clés API sont lues dans les variables d'environnement (chargées depuis le .env racine).
"""

import os

from google import genai
from google.genai import types

# Modèle Gemini le moins coûteux accessible à un nouveau projet (voir PLAN.md)
GEMINI_MODEL = "gemini-3.1-flash-lite"
TEMPERATURE = 0.1
# Réflexion au minimum pour limiter les tokens de sortie
GEMINI_THINKING_LEVEL = types.ThinkingLevel.MINIMAL

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


def gemini(prompt: str, system: str | None = None) -> str:
    """Envoie le prompt à Gemini et renvoie la réponse texte."""
    response = _get_gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=TEMPERATURE,
            thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL),
        ),
    )
    return response.text or ""
