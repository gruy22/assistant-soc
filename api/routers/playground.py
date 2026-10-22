"""Interface de test des LLM : page de chat et endpoint pour interroger un fournisseur."""

import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from llm.clients import PROVIDERS

PAGE = Path(__file__).resolve().parent.parent / "static" / "playground.html"

router = APIRouter(prefix="/playground", tags=["playground"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    provider: str
    prompt: str = Field(min_length=1)
    # Messages précédents de la conversation ; les clients LLM n'en gardent que les derniers
    history: list[ChatMessage] = []


class AskResponse(BaseModel):
    provider: str
    model: str
    answer: str
    duration_s: float


@router.get("", include_in_schema=False)
def page() -> FileResponse:
    """Page de chat pour tester les fournisseurs LLM."""
    return FileResponse(PAGE)


@router.get("/providers")
def providers() -> dict[str, str]:
    """Fournisseurs disponibles et modèle utilisé par chacun."""
    return {name: model for name, (_, model) in PROVIDERS.items()}


@router.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    """Envoie le prompt au fournisseur choisi et renvoie sa réponse."""
    if request.provider not in PROVIDERS:
        raise HTTPException(400, f"Fournisseur inconnu : {request.provider}")
    call, model = PROVIDERS[request.provider]
    start = time.perf_counter()
    try:
        answer = call(request.prompt, None, [m.model_dump() for m in request.history])
    except Exception as exc:
        raise HTTPException(502, f"Erreur {request.provider} : {type(exc).__name__} : {exc}") from exc
    return AskResponse(
        provider=request.provider,
        model=model,
        answer=answer,
        duration_s=round(time.perf_counter() - start, 1),
    )
