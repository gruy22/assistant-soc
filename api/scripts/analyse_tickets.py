"""Analyse les tickets de data/tickets.json avec un LLM et compte les tickets par sévérité.

Chaque ticket est envoyé à l'endpoint POST /playground/ask de l'API (qui doit tourner).
Le playground utilise aussi ce script (fonction `run_analysis`) pour ses boutons d'analyse.

Usage (depuis api/) :
    uv run python scripts/analyse_tickets.py --provider gemini
    uv run python scripts/analyse_tickets.py --provider phi4 --limit 10 --output resultats.json
    uv run python scripts/analyse_tickets.py --provider phi4 --rapide   # sévérité seule, bien plus rapide
"""

import argparse
import json
import re
import threading
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

TICKETS_FILE = Path(__file__).resolve().parents[2] / "data" / "tickets.json"
SEVERITIES = ["HIGH", "MEDIUM", "LOW", "INCERTITUDE"]
# Ligne « Sévérité : HIGH » du format de sortie imposé par le prompt SOC (gras Markdown toléré)
SEVERITY_RE = re.compile(r"s[ée]v[ée]rit[ée]\W*(HIGH|MEDIUM|LOW|INCERTITUDE)", re.IGNORECASE)
TIMEOUT_S = 600
# Mode rapide : seule la sévérité est demandée. L'explication et les actions représentent
# l'essentiel des tokens générés, donc du temps d'analyse (≈ 140 tokens par ticket).
# Les modèles ignorent souvent la consigne (le prompt SOC impose le format complet) : la réponse
# est donc aussi coupée après FAST_MAX_TOKENS, la ligne « Sévérité » arrivant en premier.
FAST_INSTRUCTIONS = (
    "Mode tri rapide : réponds uniquement par la ligne « Sévérité : <HIGH, MEDIUM, LOW ou incertitude> », "
    "sans explication ni actions."
)
FAST_MAX_TOKENS = 12
# Ollama sur CPU traite un appel à la fois : en envoyer plusieurs ne fait que créer une file
# d'attente et favorise ses erreurs 500 intermittentes.
DEFAULT_WORKERS = {"phi4": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", required=True, help="fournisseur enregistré (ex. gemini, phi4)")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="adresse de l'API")
    parser.add_argument("--limit", type=int, help="n'analyser que les N premiers tickets")
    parser.add_argument("--workers", type=int, help="appels simultanés (défaut : 1 pour phi4, 4 sinon)")
    parser.add_argument("--output", type=Path, help="fichier JSON où enregistrer le détail par ticket")
    parser.add_argument("--rapide", action="store_true", help="ne demander que la sévérité (bien plus rapide)")
    return parser.parse_args()


def extract_severity(answer: str) -> str:
    match = SEVERITY_RE.search(answer)
    return match.group(1).upper() if match else "NON RECONNUE"


def analyse(client: httpx.Client, url: str, provider: str, ticket: dict, fast: bool = False) -> dict:
    """Envoie un ticket à l'API et renvoie sa sévérité (ou l'erreur)."""
    prompt = "Analyse ce ticket SOC :\n" + json.dumps(ticket, ensure_ascii=False, indent=2)
    payload = {"provider": provider, "prompt": prompt}
    if fast:
        payload |= {"system": FAST_INSTRUCTIONS, "max_tokens": FAST_MAX_TOKENS}
    try:
        response = client.post(f"{url}/playground/ask", json=payload)
        data = response.json()
        if response.is_error:
            return {"id": ticket["id"], "severity": "ERREUR", "error": data.get("detail", response.text)}
        return {"id": ticket["id"], "severity": extract_severity(data["answer"]), "answer": data["answer"]}
    except (httpx.HTTPError, ValueError) as exc:
        return {"id": ticket["id"], "severity": "ERREUR", "error": f"{type(exc).__name__} : {exc}"}


def load_tickets(limit: int | None = None) -> list[dict]:
    return json.loads(TICKETS_FILE.read_text(encoding="utf-8"))[:limit]


def run_analysis(
    url: str,
    provider: str,
    tickets: list[dict],
    workers: int | None = None,
    on_result: Callable[[dict], None] | None = None,
    stop: threading.Event | None = None,
    fast: bool = False,
) -> list[dict]:
    """Analyse les tickets en parallèle ; `on_result` est appelé après chaque ticket.

    Si `stop` est déclenché, les tickets pas encore envoyés sont abandonnés.
    `fast` : mode rapide, seule la sévérité est demandée au modèle.
    `workers` : appels simultanés ; par défaut DEFAULT_WORKERS[provider], sinon 4.
    """
    workers = workers or DEFAULT_WORKERS.get(provider, 4)
    results = []
    with httpx.Client(timeout=TIMEOUT_S) as client, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(analyse, client, url, provider, t, fast) for t in tickets]
        for future in as_completed(futures):
            if future.cancelled():
                continue
            result = future.result()
            results.append(result)
            if on_result:
                on_result(result)
            if stop and stop.is_set():
                for f in futures:
                    f.cancel()
    return results


def main() -> None:
    args = parse_args()
    tickets = load_tickets(args.limit)

    providers = httpx.get(f"{args.url}/playground/providers").json()
    if args.provider not in providers:
        raise SystemExit(f"Fournisseur inconnu : {args.provider} (disponibles : {', '.join(providers)})")
    print(f"{len(tickets)} tickets à analyser avec {args.provider} ({providers[args.provider]}), "
          f"mode {'rapide' if args.rapide else 'complet'}, "
          f"{args.workers or DEFAULT_WORKERS.get(args.provider, 4)} appel(s) simultané(s)\n")

    done = 0

    def show(result: dict) -> None:
        nonlocal done
        done += 1
        print(f"[{done}/{len(tickets)}] {result['id']} : {result['severity']}")

    start = time.perf_counter()
    results = run_analysis(args.url, args.provider, tickets, args.workers, on_result=show, fast=args.rapide)
    elapsed = time.perf_counter() - start

    counts = Counter(r["severity"] for r in results)
    print(f"\nRésultat ({len(results)} tickets, {elapsed:.0f} s) :")
    for severity in SEVERITIES + sorted(set(counts) - set(SEVERITIES)):
        print(f"  {severity:<13} {counts.get(severity, 0)}")

    errors = [r for r in results if r["severity"] == "ERREUR"]
    for r in errors[:5]:
        print(f"  Erreur {r['id']} : {r['error']}")

    if args.output:
        results.sort(key=lambda r: r["id"])
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nDétail enregistré dans {args.output}")


if __name__ == "__main__":
    main()
