"""Interface de test des LLM : page de chat, endpoint pour interroger un fournisseur
et analyse en lot des tickets (via scripts/analyse_tickets.py) lancée depuis la page."""

import threading
import time
from collections import Counter
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from llm.clients import PROVIDERS
from scripts.analyse_tickets import load_tickets, run_analysis

PAGE = Path(__file__).resolve().parent.parent / "static" / "playground.html"

router = APIRouter(prefix="/playground", tags=["playground"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    provider: str
    prompt: str = Field(min_length=1)
    # Instructions ajoutées à la suite du prompt système SOC (qui reste toujours appliqué)
    system: str | None = None
    # Limite de tokens générés (utilisée par le mode rapide de l'analyse en lot)
    max_tokens: int | None = Field(default=None, ge=1)
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
        answer = call(request.prompt, request.system, [m.model_dump() for m in request.history], request.max_tokens)
    except Exception as exc:
        raise HTTPException(502, f"Erreur {request.provider} : {type(exc).__name__} : {exc}") from exc
    return AskResponse(
        provider=request.provider,
        model=model,
        answer=answer,
        duration_s=round(time.perf_counter() - start, 1),
    )


# --- Analyse en lot des tickets ------------------------------------------------
# Une analyse au plus par fournisseur ; l'état est en mémoire (perdu si le serveur redémarre,
# y compris lors d'un rechargement automatique après modification d'un fichier .py).

class AnalysisJob:
    def __init__(self, provider: str, total: int, mode: str) -> None:
        self.provider = provider
        self.total = total
        self.mode = mode  # "rapide" (sévérité seule) ou "complet"
        self.done = 0
        self.counts: Counter[str] = Counter()
        self.errors: list[str] = []
        self.status = "running"  # running, stopping, stopped, done
        self.started = time.time()
        self.finished: float | None = None
        self.stop = threading.Event()
        self.lock = threading.Lock()

    def add(self, result: dict) -> None:
        with self.lock:
            self.done += 1
            self.counts[result["severity"]] += 1
            if result["severity"] == "ERREUR" and len(self.errors) < 5:
                self.errors.append(f"{result['id']} : {result['error']}")

    def snapshot(self) -> dict:
        with self.lock:
            elapsed = (self.finished or time.time()) - self.started
            remaining = self.total - self.done
            # Estimation au débit moyen observé depuis le début
            eta = elapsed / self.done * remaining if self.done and self.status == "running" else None
            return {
                "provider": self.provider,
                "model": PROVIDERS[self.provider][1],
                "mode": self.mode,
                "status": self.status,
                "total": self.total,
                "done": self.done,
                "counts": dict(self.counts),
                "errors": self.errors,
                "elapsed_s": round(elapsed),
                "eta_s": round(eta) if eta is not None else None,
                # Débit moyen (appels simultanés compris) : temps réel par ticket
                "per_ticket_s": round(elapsed / self.done, 1) if self.done else None,
            }


_jobs: dict[str, AnalysisJob] = {}
_jobs_lock = threading.Lock()


def _run_job(job: AnalysisJob, url: str, tickets: list[dict]) -> None:
    try:
        run_analysis(url, job.provider, tickets, on_result=job.add, stop=job.stop, fast=job.mode == "rapide")
    finally:
        with job.lock:
            job.status = "stopped" if job.stop.is_set() else "done"
            job.finished = time.time()


@router.get("/analysis")
def analysis_status() -> dict:
    """Nombre de tickets disponibles et état de la dernière analyse de chaque fournisseur."""
    return {
        "tickets_total": len(load_tickets()),
        "jobs": {name: job.snapshot() for name, job in _jobs.items()},
    }


class StartRequest(BaseModel):
    # Nombre de tickets à analyser (les premiers du fichier) ; absent = tous
    limit: int | None = Field(default=None, ge=1)
    # « rapide » : sévérité seule ; « complet » : sévérité, explication et actions
    mode: Literal["rapide", "complet"] = "complet"


@router.post("/analysis/{provider}/start")
def analysis_start(provider: str, request: Request, body: StartRequest | None = None) -> dict:
    """Lance l'analyse des tickets avec le fournisseur choisi."""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Fournisseur inconnu : {provider}")
    body = body or StartRequest()
    with _jobs_lock:
        current = _jobs.get(provider)
        if current and current.status in ("running", "stopping"):
            raise HTTPException(409, f"Une analyse {provider} est déjà en cours")
        tickets = load_tickets(body.limit)
        job = AnalysisJob(provider, len(tickets), body.mode)
        _jobs[provider] = job
    # Le script appelle /playground/ask sur cette même API
    url = str(request.base_url).rstrip("/")
    threading.Thread(target=_run_job, args=(job, url, tickets), daemon=True).start()
    return job.snapshot()


@router.post("/analysis/{provider}/stop")
def analysis_stop(provider: str) -> dict:
    """Arrête l'analyse : les tickets en cours se terminent, les suivants ne sont pas envoyés."""
    job = _jobs.get(provider)
    if not job or job.status != "running":
        raise HTTPException(409, f"Aucune analyse {provider} en cours")
    with job.lock:
        job.status = "stopping"
    job.stop.set()
    return job.snapshot()
