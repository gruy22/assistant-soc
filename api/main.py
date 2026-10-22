"""Point d'entrée de l'application FastAPI de l'assistant SOC."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Le .env est à la racine du projet (un niveau au-dessus de api/)
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_FILE)

app = FastAPI(title="Assistant SOC")


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que l'API répond."""
    return {"status": "ok"}
