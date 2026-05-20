# Mini Projeto 3 — Consumo de APIs

**Fatec Rio Claro · Análise e Desenvolvimento de Sistemas**  
Disciplina: Desenvolvimento de Sistemas · Tema: Consumo de APIs

---

## Sobre o projeto

Este projeto demonstra na prática como APIs REST permitem a comunicação padronizada entre sistemas independentes. A aplicação implementa um pipeline completo: um servidor que expõe endpoints HTTP e um cliente que os consome — o mesmo padrão usado em integrações reais com serviços de NLP, visão computacional e outros modelos de ML.

O domínio escolhido foi **análise de sentimento em português**. O servidor recebe um texto via requisição HTTP, processa e devolve uma classificação (`positivo`, `negativo` ou `neutro`) junto de um score normalizado e os tokens que influenciaram o resultado.

---

## Arquitetura

```
┌─────────────────────────────────────────────────┐
│                   app.py (GUI)                  │
│                                                 │
│   ┌─────────────────┐     ┌──────────────────┐  │
│   │  FastAPI Server │     │  Tkinter Client  │  │
│   │  (thread daemon)│◄────│  (thread daemon) │  │
│   │  127.0.0.1:8000 │     │                  │  │
│   └─────────────────┘     └──────────────────┘  │
└─────────────────────────────────────────────────┘

Fluxo de uma análise:
  GUI → requests.post(/analyze) → FastAPI → _analyze() → JSON → GUI
```

O servidor e o cliente rodam no mesmo processo (`app.py`), cada um em sua própria thread. A comunicação entre eles é feita exclusivamente via HTTP — exatamente como ocorreria se fossem sistemas em máquinas distintas.

---

## Stack

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| Servidor | FastAPI + Uvicorn | API REST assíncrona |
| Validação | Pydantic v2 | Schema e validação do payload |
| Cliente HTTP | Requests | Consumo dos endpoints |
| Interface | Tkinter | GUI nativa, sem dependências externas |
| Configuração | python-dotenv | Variáveis de ambiente via `.env` |

---

## Estrutura de arquivos

```
eu_projeto_api/
├── app.py               ← ponto de entrada único (GUI + servidor embutido)
├── requirements.txt
├── install.bat          ← instala dependências e cria venv (Windows)
├── README.md
├── server/
│   ├── main.py          ← servidor FastAPI isolado (uso via terminal)
│   └── .env.example
└── client/
    └── main.py          ← cliente terminal com auto-instalação de deps
```

---

## Como executar

### Interface gráfica (recomendado)

```bat
python app.py
```

Na primeira execução, o bootstrap detecta dependências ausentes, instala via pip e reinicia o processo automaticamente com `os.execv`. A janela abre assim que o servidor estiver pronto.

### Terminal (modo separado)

Instale as dependências:

```bat
pip install -r requirements.txt
```

Terminal 1 — servidor:

```bat
cd server
uvicorn main:app --reload
```

Terminal 2 — cliente (roda análises em lote com 6 frases de exemplo):

```bat
cd client
python main.py
```

---

## Endpoints

### `GET /health`
Verifica se o servidor está no ar.

**Response:**
```json
{ "status": "ok", "timestamp": 1718200000 }
```

---

### `POST /analyze`
Recebe um texto e retorna a análise de sentimento.

**Headers:**
```
X-API-Key: dev-key-local
Content-Type: application/json
```

**Body:**
```json
{ "text": "O produto chegou antes do prazo e a qualidade é excelente!" }
```

**Response:**
```json
{
  "sentiment": "positivo",
  "score": 0.8333,
  "tokens_analyzed": 11,
  "highlights": ["excelente"]
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `sentiment` | string | `positivo`, `negativo` ou `neutro` |
| `score` | float | Score normalizado entre `0.0` e `1.0` |
| `tokens_analyzed` | int | Total de tokens processados no texto |
| `highlights` | array | Palavras que influenciaram a classificação |

---

### `GET /analyze/history`
Retorna as últimas 50 análises realizadas na sessão atual (armazenadas em memória).

**Response:**
```json
{
  "count": 3,
  "items": [
    { "text": "Produto excelente...", "sentiment": "positivo", "score": 0.83, "tokens_analyzed": 4, "highlights": ["excelente"] }
  ]
}
```

---

## Como funciona a análise

O algoritmo usa correspondência léxica com dois vocabulários em português:

1. O texto é tokenizado e normalizado (lowercase, remoção de pontuação)
2. Cada token é verificado contra `POSITIVE_WORDS` e `NEGATIVE_WORDS`
3. O score bruto é calculado como `(positivos - negativos) / total_tokens`
4. O valor é normalizado para o intervalo `[0.0, 1.0]` com fator de amplificação `×5`
5. A classificação final segue: `score > 0.55` → positivo · `score < 0.45` → negativo · demais → neutro

Essa abordagem é intencionalmente simples para manter o foco na demonstração da arquitetura de APIs — em produção, esse endpoint poderia ser substituído por uma chamada a modelos como BERT, GPT ou qualquer serviço externo sem alterar o contrato da API.

---

## Autenticação

Todos os endpoints protegidos exigem o header `X-API-Key`. O valor padrão para desenvolvimento é `dev-key-local`, configurável via variável de ambiente `API_KEY` no arquivo `.env`.

```
# server/.env
API_KEY=dev-key-local
HOST=0.0.0.0
PORT=8000
```
