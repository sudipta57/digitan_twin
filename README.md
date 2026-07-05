# Dead People's Digital Twin

> Source-grounded conversations with history's greatest minds — and, if you set it up, with someone you actually knew.
> Built for WeMakeDevs × Cognee Hackathon 2026.

## The Problem

Existing "talk to historical figures" AI tools hallucinate responses, invent quotes, and present fiction as fact. There is no grounding, no citation, no acknowledgment of contradictions in a person's evolving worldview.

## The Solution

A source-grounded memory system that ingests everything a historical figure ever wrote, said, or published — and builds a **hybrid graph-vector knowledge store** of their actual documented worldview using Cognee Cloud.

Two modes:
- **Public figures** — pre-ingested historical figures (Feynman, Tesla, Curie*) available to everyone, no login required.
- **Personal twins** — sign in with Google, upload your own source material (WhatsApp exports, letters, PDFs, plain text) about someone you knew, and build a private memory graph of them. Fully isolated per user.

*\*Curie is listed as a public figure but currently has no ingested source material — see [Running Locally](#running-locally).*

Every response is:
- Grounded in real, ingested source material
- Cited with exact source, year, and document
- Honest about contradictions across time
- Transparent when extrapolating vs directly quoting

## Demo

[[Demo video]](https://youtu.be/LK0iXbZXF2s)

## How It Works

```
User question
    │
    ▼
POST /chat  →  CogneeService.query_figure() → cognee.recall(question, query_type=CHUNKS)
    │
    ▼
LLM (Gemini or GLM-5, depending on LLM_PROVIDER)
    ←  real memory chunks + contradiction data + persona
    │
    ▼
Response with citations + confidence badge (direct / extrapolated / speculative)
```

## Cognee API Usage

| Method | Where used |
|--------|-----------|
| `cognee.remember()` | Ingest tagged source chunks into a figure's isolated dataset (`figure_{figure_id}`) |
| `cognee.cognify()` | Build the knowledge graph from ingested chunks after each ingest |
| `cognee.recall()` (`query_type=CHUNKS`) | Retrieve the real, traceable source text for a question — not a synthesized answer — so every reply stays grounded in cited material |
| `cognee.forget()` | Permanently delete a figure's dataset when a personal twin is deleted |

Topic and contradiction detection are **not** separate Cognee calls — the backend recalls the relevant raw chunks from Cognee, then asks its own LLM to read those chunks and extract topics / contradictions as structured JSON (see `LLMService.extract_topics` / `extract_contradictions`).

## Stack

FastAPI · React + TypeScript · Tailwind CSS · Cognee Cloud · Google Gemini or GLM-5 (via AWS Bedrock Mantle) · Google OAuth · Railway · Vercel

The LLM backend is switchable per-deployment via `LLM_PROVIDER` (`gemini` or `openai`) — see below.

## Running Locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env with:
#   COGNEE_API_KEY / COGNEE_BASE_URL   — platform.cognee.ai/api-keys
#   LLM_PROVIDER=gemini                — or "openai" for GLM-5 via AWS Bedrock Mantle
#   GEMINI_API_KEY (if LLM_PROVIDER=gemini)
#   OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL (if LLM_PROVIDER=openai)
#   GOOGLE_CLIENT_ID / SESSION_SECRET  — required for the personal-twin login flow

# Start server (from project root, not from backend/)
cd ..
uvicorn backend.main:app --reload

# Pre-ingest source material for Feynman + Tesla (Curie has no seed data yet)
python -m backend.data.seed
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local:
#   VITE_API_URL=http://localhost:8000
#   VITE_GOOGLE_CLIENT_ID=<same client ID as backend's GOOGLE_CLIENT_ID>  — needed for the "My Twins" login button
npm run dev
```

Open http://localhost:5173

Without `GOOGLE_CLIENT_ID`/`VITE_GOOGLE_CLIENT_ID` set, the app still works fully for public figures — the login button just renders as "Google sign-in not configured" and personal twins stay inaccessible.

## Deployment

**Backend → Railway**
- Connect GitHub repo, set root to `/backend`
- Set env vars: `COGNEE_API_KEY`, `COGNEE_BASE_URL`, `LLM_PROVIDER`, `GEMINI_API_KEY` and/or `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL`, `GOOGLE_CLIENT_ID`, `SESSION_SECRET`, `FRONTEND_URL`, `ENVIRONMENT=production`
- Railway uses `Procfile` automatically

**Frontend → Vercel**
- Connect GitHub repo, set root to `/frontend`
- Set env vars: `VITE_API_URL=https://your-app.up.railway.app`, `VITE_GOOGLE_CLIENT_ID`

## Project Structure

```
digital-twin/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── routers/
│   │   ├── auth.py                # POST /auth/google, GET /auth/me, POST /auth/logout
│   │   ├── figures.py             # GET/POST /figures, DELETE /figures/{id}
│   │   ├── ingest.py              # POST /ingest
│   │   ├── chat.py                # POST /chat
│   │   └── graph.py               # GET /topics, /contradictions, DELETE /source
│   ├── services/
│   │   ├── cognee_service.py      # All Cognee Cloud interactions (remember/cognify/recall/forget)
│   │   ├── llm_service.py         # Persona + prompt building, Gemini/OpenAI calls, response parsing
│   │   ├── parser_service.py      # PDF/URL/text/WhatsApp chunking
│   │   ├── auth_service.py        # Google ID token verification
│   │   ├── session.py             # Signed session cookie (itsdangerous)
│   │   └── figure_store.py        # In-memory personal-figure metadata store
│   ├── models/
│   │   ├── schemas.py             # Pydantic request/response models
│   │   └── constants.py           # Public figure definitions
│   └── data/
│       ├── seed.py                # One-time corpus ingestion script (Feynman + Tesla)
│       └── figures/                # Portrait SVGs (feynman/tesla/curie)
│
└── frontend/
    └── src/
        ├── components/            # Sidebar, ChatWindow, CitationCard, ConfidenceBadge,
        │                          # ContradictionLog, CreateTwinModal, LoginButton
        ├── context/AuthContext.tsx # Google login session state
        ├── hooks/                 # useChat, useFigure
        ├── api/                   # Axios client
        └── types/                 # TypeScript interfaces
```

## Team - Aloo Siddo

Sudipta Ghorami
Piyush Paul
Samiran Pal
Tiasha Biswas
