# Dead People's Digital Twin

> Source-grounded conversations with history's greatest minds.
> Built for WeMakeDevs × Cognee Hackathon 2026.

## The Problem

Existing "talk to historical figures" AI tools hallucinate responses, invent quotes, and present fiction as fact. There is no grounding, no citation, no acknowledgment of contradictions in a person's evolving worldview.

## The Solution

A source-grounded memory system that ingests everything a historical figure ever wrote, said, or published — and builds a **hybrid graph-vector knowledge store** of their actual documented worldview using Cognee Cloud.

Every response is:
- Grounded in real, ingested source material
- Cited with exact source, year, and document
- Honest about contradictions across time
- Transparent when extrapolating vs directly quoting

## Demo

[Add demo video link after recording]

## How It Works

```
User question
    │
    ▼
POST /chat  →  cognee.recall(question, dataset=figure)
    │
    ▼
GLM-5 (z.ai)  ←  memory context + contradiction data + persona
    │
    ▼
Response with citations + confidence badge (direct / extrapolated / speculative)
```

## Cognee API Usage

| Method | Where used |
|--------|-----------|
| `remember()` | Ingest source material chunks into figure's dataset |
| `recall()` | Graph traversal + semantic search for chat context |
| `improve()` | Contradiction detection — re-weights graph nodes |
| `forget()` | Remove disputed or misattributed sources |

## Stack

FastAPI · React + TypeScript · Tailwind CSS · Cognee Cloud · GLM-5 (z.ai) · Railway · Vercel

## Running Locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env with your COGNEE_API_KEY and ZAI_API_KEY

# Start server
uvicorn backend.main:app --reload

# Pre-ingest source material
python -m backend.data.seed
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local: VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173

## Deployment

**Backend → Railway**
- Connect GitHub repo, set root to `/backend`
- Set env vars: `COGNEE_API_KEY`, `ZAI_API_KEY`, `FRONTEND_URL`
- Railway uses `Procfile` automatically

**Frontend → Vercel**
- Connect GitHub repo, set root to `/frontend`
- Set env var: `VITE_API_URL=https://your-app.up.railway.app`

## Project Structure

```
digital-twin/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── routers/
│   │   ├── ingest.py            # POST /ingest
│   │   ├── chat.py              # POST /chat
│   │   └── graph.py             # GET /figures, /topics, /contradictions, DELETE /source
│   ├── services/
│   │   ├── cognee_service.py    # All Cognee Cloud interactions
│   │   ├── llm_service.py       # Gemini prompt building + response parsing
│   │   └── parser_service.py    # PDF/URL/text chunking
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   └── data/
│       └── seed.py              # One-time corpus ingestion script
│
└── frontend/
    └── src/
        ├── components/          # FigureSelector, ChatWindow, CitationCard, ContradictionLog
        ├── hooks/               # useChat, useFigure
        ├── api/                 # Axios client
        └── types/               # TypeScript interfaces
```

## Team

[Add team members + roles]
