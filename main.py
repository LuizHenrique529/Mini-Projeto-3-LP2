import os
import time
from collections import deque
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, field_validator

load_dotenv()

API_KEY = os.getenv("API_KEY", "dev-key-local")

app = FastAPI(title="Sentiment API", version="1.0.0")

_history: deque = deque(maxlen=50)

POSITIVE_WORDS = {
    "excelente", "ótimo", "incrível", "bom", "maravilhoso", "perfeito",
    "rápido", "eficiente", "adorei", "gostei", "recomendo", "feliz",
    "satisfeito", "aprovado", "funciona", "parabéns", "top", "incrivel",
    "otimo", "satisfacao", "satisfação", "qualidade", "confiável",
}

NEGATIVE_WORDS = {
    "péssimo", "horrível", "ruim", "lento", "quebrou", "defeito",
    "decepcionante", "decepcionei", "odiei", "detestei", "problema",
    "travou", "falhou", "fraude", "mentira", "arrependido", "horrivel",
    "pessimo", "terrível", "terrivel", "pior", "errado", "demora",
}


def _check_key(key: str | None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")


class AnalyzeRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text não pode ser vazio")
        if len(v) > 2000:
            raise ValueError("text excede o limite de 2000 caracteres")
        return v


def _analyze(text: str) -> dict:
    tokens = [t.lower().strip(".,!?;:\"'()") for t in text.split()]
    tokens = [t for t in tokens if t]

    pos_hits = [t for t in tokens if t in POSITIVE_WORDS]
    neg_hits = [t for t in tokens if t in NEGATIVE_WORDS]

    total = len(tokens) or 1
    raw_score = (len(pos_hits) - len(neg_hits)) / total

    normalized = max(-1.0, min(1.0, raw_score * 5))
    score = round((normalized + 1) / 2, 4)

    if normalized > 0.1:
        sentiment = "positivo"
    elif normalized < -0.1:
        sentiment = "negativo"
    else:
        sentiment = "neutro"

    highlights = list(dict.fromkeys(pos_hits + neg_hits))[:5]

    return {
        "sentiment": sentiment,
        "score": score,
        "tokens_analyzed": len(tokens),
        "highlights": highlights,
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": int(time.time())}


@app.post("/analyze")
def analyze(body: AnalyzeRequest, x_api_key: str | None = Header(default=None)):
    _check_key(x_api_key)
    result = _analyze(body.text)
    _history.appendleft({"text": body.text[:120], **result})
    return result


@app.get("/analyze/history")
def history(x_api_key: str | None = Header(default=None)):
    _check_key(x_api_key)
    return {"count": len(_history), "items": list(_history)}
