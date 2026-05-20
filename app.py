import subprocess
import sys
import importlib.util
import os

# ── bootstrap ─────────────────────────────────────────────────────────────────
_DEPS = {
    "fastapi":       "fastapi",
    "uvicorn":       "uvicorn",
    "requests":      "requests",
    "python-dotenv": "dotenv",
    "pydantic":      "pydantic",
}

def _bootstrap():
    missing = [pkg for pkg, mod in _DEPS.items()
               if importlib.util.find_spec(mod) is None]
    if not missing:
        return

    # Mostra aviso visual antes de instalar
    try:
        import tkinter as tk
        import tkinter.messagebox as mb
        root = tk.Tk()
        root.withdraw()
        mb.showinfo(
            "Primeira execução",
            "Instalando dependências necessárias:\n\n" +
            "\n".join(f"  • {p}" for p in missing) +
            "\n\nO programa vai reiniciar automaticamente."
        )
        root.destroy()
    except Exception:
        print(f"[setup] Instalando: {', '.join(missing)}")

    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", *missing
    ])

    # Reinicia o script para que os módulos instalados sejam encontrados
    os.execv(sys.executable, [sys.executable] + sys.argv)

_bootstrap()

# ── imports (garantidos após bootstrap) ──────────────────────────────────────
import time
import threading
import tkinter as tk
from tkinter import scrolledtext
from collections import deque

import requests as req
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, field_validator

# ── servidor FastAPI (embutido) ───────────────────────────────────────────────
API_KEY = "dev-key-local"

import unicodedata

_app = FastAPI()
_history: deque = deque(maxlen=50)

# vocabulário normalizado sem acentos
POSITIVE_WORDS = {
    "excelente", "otimo", "otima", "incrivel", "bom", "boa", "maravilhoso",
    "maravilhosa", "perfeito", "perfeita", "rapido", "rapida", "eficiente",
    "adorei", "gostei", "amei", "recomendo", "feliz", "satisfeito", "satisfeita",
    "aprovado", "aprovada", "funciona", "funcionou", "parabens", "top", "legal",
    "satisfacao", "qualidade", "confiavel", "lindo", "linda", "bonito", "bonita",
    "agradavel", "facil", "pratico", "pratica", "pontual", "util", "economico",
    "barato", "barata", "resistente", "duravel", "moderno", "moderna",
    "atencioso", "atenciosa", "educado", "educada", "gentil", "honesto", "honesta",
}
NEGATIVE_WORDS = {
    "pessimo", "pessima", "horrivel", "ruim", "lento", "lenta", "quebrou",
    "quebrado", "quebrada", "defeito", "decepcionante", "decepcionei", "odiei",
    "detestei", "problema", "problemas", "travou", "falhou", "fraude", "mentira",
    "arrependido", "arrependida", "terrivel", "pior", "errado", "errada",
    "demora", "demorou", "atrasou", "atrasado", "atrasada", "caro", "cara",
    "fragil", "fraco", "fraca", "inutil", "grosseiro", "grosseira", "descaso",
    "descuidado", "descuidada", "falso", "falsa", "enganosa", "enganoso",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


class _Req(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("vazio")
        return v[:2000]


def _analyze(text: str) -> dict:
    raw_tokens = [t.lower().strip(".,!?;:\"'()[]") for t in text.split() if t]
    raw_tokens = [t for t in raw_tokens if t]
    norm_tokens = [_strip_accents(t) for t in raw_tokens]

    pos = [raw_tokens[i] for i, t in enumerate(norm_tokens) if t in POSITIVE_WORDS]
    neg = [raw_tokens[i] for i, t in enumerate(norm_tokens) if t in NEGATIVE_WORDS]

    total = len(norm_tokens) or 1
    norm = max(-1.0, min(1.0, ((len(pos) - len(neg)) / total) * 5))
    score = round((norm + 1) / 2, 4)
    sentiment = "positivo" if norm > 0.1 else ("negativo" if norm < -0.1 else "neutro")
    return {
        "sentiment": sentiment,
        "score": score,
        "tokens_analyzed": len(norm_tokens),
        "highlights": list(dict.fromkeys(pos + neg))[:5],
    }

def _check_key(key):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")

@_app.get("/health")
def _health():
    return {"status": "ok"}

@_app.post("/analyze")
def _do_analyze(body: _Req, x_api_key: str | None = Header(default=None)):
    _check_key(x_api_key)
    r = _analyze(body.text)
    _history.appendleft({"text": body.text[:120], **r})
    return r

@_app.get("/analyze/history")
def _do_history(x_api_key: str | None = Header(default=None)):
    _check_key(x_api_key)
    return {"count": len(_history), "items": list(_history)}

def _start_server():
    uvicorn.run(_app, host="127.0.0.1", port=8000, log_level="error")

# ── Interface Gráfica ─────────────────────────────────────────────────────────
BASE   = "http://127.0.0.1:8000"
HDR    = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
COLORS = {
    "bg":       "#1e1e2e",
    "surface":  "#2a2a3e",
    "accent":   "#7c6af7",
    "positive": "#4ade80",
    "negative": "#f87171",
    "neutral":  "#94a3b8",
    "text":     "#e2e8f0",
    "muted":    "#64748b",
    "border":   "#3a3a5c",
}

SENTIMENT_EMOJI = {"positivo": "😊", "negativo": "😞", "neutro": "😐"}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Análise de Sentimento — Fatec Rio Claro")
        self.geometry("780x620")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self._server_ready = False
        self._build_ui()
        self._start_server_thread()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=COLORS["accent"], height=54)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="  Análise de Sentimento via API",
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["accent"], fg="white", anchor="w"
        ).pack(side="left", padx=16, pady=12)

        self._status_dot = tk.Label(hdr, text="●  Iniciando servidor...",
            font=("Segoe UI", 9), bg=COLORS["accent"], fg="#c8c4f0")
        self._status_dot.pack(side="right", padx=16)

        mid = tk.Frame(self, bg=COLORS["bg"])
        mid.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(mid, text="Texto para análise", font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor="w")

        self._input = tk.Text(mid, height=5, font=("Segoe UI", 11),
            bg=COLORS["surface"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            bd=0, padx=10, pady=8, wrap="word")
        self._input.pack(fill="x", pady=(6, 0))
        self._input.bind("<Control-Return>", lambda e: self._analyze())

        btn_row = tk.Frame(self, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=24, pady=10)

        self._btn = tk.Button(btn_row, text="Analisar  (Ctrl+Enter)",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["accent"], fg="white", activebackground="#6354d4",
            relief="flat", cursor="hand2", padx=18, pady=7,
            command=self._analyze)
        self._btn.pack(side="left")

        tk.Button(btn_row, text="Limpar", font=("Segoe UI", 10),
            bg=COLORS["surface"], fg=COLORS["muted"], activebackground=COLORS["border"],
            relief="flat", cursor="hand2", padx=14, pady=7,
            command=self._clear).pack(side="left", padx=10)

        tk.Button(btn_row, text="Ver Histórico", font=("Segoe UI", 10),
            bg=COLORS["surface"], fg=COLORS["muted"], activebackground=COLORS["border"],
            relief="flat", cursor="hand2", padx=14, pady=7,
            command=self._show_history).pack(side="right")

        self._card = tk.Frame(self, bg=COLORS["surface"], bd=0)
        self._card.pack(fill="x", padx=24, pady=(0, 14))

        self._emoji_lbl = tk.Label(self._card, text="", font=("Segoe UI", 36),
            bg=COLORS["surface"])
        self._emoji_lbl.pack(side="left", padx=20, pady=16)

        info = tk.Frame(self._card, bg=COLORS["surface"])
        info.pack(side="left", fill="both", expand=True, pady=14)

        self._sent_lbl = tk.Label(info, text="—", font=("Segoe UI", 18, "bold"),
            bg=COLORS["surface"], fg=COLORS["text"], anchor="w")
        self._sent_lbl.pack(anchor="w")

        self._score_lbl = tk.Label(info, text="", font=("Segoe UI", 10),
            bg=COLORS["surface"], fg=COLORS["muted"], anchor="w")
        self._score_lbl.pack(anchor="w")

        self._bar_canvas = tk.Canvas(info, height=10, bg=COLORS["surface"],
            highlightthickness=0)
        self._bar_canvas.pack(fill="x", pady=(6, 4))

        self._hl_lbl = tk.Label(info, text="", font=("Segoe UI", 9),
            bg=COLORS["surface"], fg=COLORS["muted"], anchor="w")
        self._hl_lbl.pack(anchor="w")

        tk.Label(self, text="Log de análises", font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=26)

        self._log = scrolledtext.ScrolledText(self, height=9,
            font=("Consolas", 9), bg=COLORS["surface"], fg=COLORS["muted"],
            insertbackground=COLORS["text"], relief="flat", bd=0,
            padx=10, pady=8, state="disabled")
        self._log.pack(fill="both", expand=True, padx=24, pady=(4, 20))

        self._log.tag_config("pos", foreground=COLORS["positive"])
        self._log.tag_config("neg", foreground=COLORS["negative"])
        self._log.tag_config("neu", foreground=COLORS["neutral"])
        self._log.tag_config("err", foreground="#f87171")
        self._log.tag_config("sys", foreground=COLORS["accent"])

    def _start_server_thread(self):
        threading.Thread(target=_start_server, daemon=True).start()
        self.after(800, self._poll_server)

    def _poll_server(self):
        try:
            req.get(f"{BASE}/health", timeout=1).raise_for_status()
            self._server_ready = True
            self._status_dot.config(text="●  Servidor online", fg="#4ade80")
            self._log_write("Servidor iniciado em http://127.0.0.1:8000\n", "sys")
        except Exception:
            self.after(600, self._poll_server)

    def _analyze(self):
        if not self._server_ready:
            self._log_write("Aguarde o servidor iniciar...\n", "err")
            return
        text = self._input.get("1.0", "end").strip()
        if not text:
            return
        self._btn.config(state="disabled", text="Analisando...")
        threading.Thread(target=self._do_request, args=(text,), daemon=True).start()

    def _do_request(self, text: str):
        try:
            r = req.post(f"{BASE}/analyze", headers=HDR, json={"text": text}, timeout=8)
            r.raise_for_status()
            data = r.json()
            self.after(0, lambda: self._show_result(data, text))
        except Exception as e:
            self.after(0, lambda: self._log_write(f"[erro] {e}\n", "err"))
        finally:
            self.after(0, lambda: self._btn.config(state="normal",
                                                    text="Analisar  (Ctrl+Enter)"))

    def _show_result(self, data: dict, text: str):
        s   = data["sentiment"]
        sc  = data["score"]
        hl  = data["highlights"]
        col = {"positivo": COLORS["positive"], "negativo": COLORS["negative"],
               "neutro":   COLORS["neutral"]}[s]
        tag = {"positivo": "pos", "negativo": "neg", "neutro": "neu"}[s]

        self._emoji_lbl.config(text=SENTIMENT_EMOJI[s])
        self._sent_lbl.config(text=s.capitalize(), fg=col)
        self._score_lbl.config(
            text=f"Score: {sc:.4f}   ·   Tokens: {data['tokens_analyzed']}")
        self._hl_lbl.config(
            text=("Destaques: " + ", ".join(hl)) if hl
                  else "Sem palavras-chave identificadas")

        self._bar_canvas.update_idletasks()
        w = self._bar_canvas.winfo_width()
        self._bar_canvas.delete("all")
        self._bar_canvas.create_rectangle(0, 0, w, 10,
            fill=COLORS["border"], outline="")
        self._bar_canvas.create_rectangle(0, 0, int(w * sc), 10,
            fill=col, outline="")

        snippet = text[:60].replace("\n", " ")
        self._log_write(
            f"[{s.upper()}] score={sc:.2f}  "
            f"\"{snippet}{'...' if len(text) > 60 else ''}\"\n"
            f"         destaques: {', '.join(hl) if hl else '—'}\n",
            tag
        )

    def _show_history(self):
        if not self._server_ready:
            return
        try:
            data = req.get(f"{BASE}/analyze/history", headers=HDR, timeout=4).json()
            win = tk.Toplevel(self)
            win.title("Histórico da sessão")
            win.geometry("640x420")
            win.configure(bg=COLORS["bg"])
            tk.Label(win, text=f"  {data['count']} análises nesta sessão",
                font=("Segoe UI", 11, "bold"),
                bg=COLORS["bg"], fg=COLORS["text"]
            ).pack(anchor="w", padx=16, pady=12)
            box = scrolledtext.ScrolledText(win, font=("Consolas", 9),
                bg=COLORS["surface"], fg=COLORS["text"],
                relief="flat", bd=0, padx=10, pady=8)
            box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            box.tag_config("pos", foreground=COLORS["positive"])
            box.tag_config("neg", foreground=COLORS["negative"])
            box.tag_config("neu", foreground=COLORS["neutral"])
            for item in data["items"]:
                s   = item["sentiment"]
                tag = {"positivo": "pos", "negativo": "neg", "neutro": "neu"}[s]
                box.insert("end",
                    f"[{s.upper()}] score={item['score']:.2f}  "
                    f"{item['text'][:80]}\n", tag)
            box.config(state="disabled")
        except Exception as e:
            self._log_write(f"[erro histórico] {e}\n", "err")

    def _clear(self):
        self._input.delete("1.0", "end")
        self._sent_lbl.config(text="—", fg=COLORS["text"])
        self._score_lbl.config(text="")
        self._hl_lbl.config(text="")
        self._emoji_lbl.config(text="")
        self._bar_canvas.delete("all")

    def _log_write(self, msg: str, tag: str = ""):
        self._log.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log.insert("end", f"{ts}  ", "sys")
        self._log.insert("end", msg, tag)
        self._log.see("end")
        self._log.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
