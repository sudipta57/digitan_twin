# Dead People's Digital Twin — Run & Test Guide

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.13.13 | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

## API Keys Required

You need **Cognee** plus **one** LLM provider:

| Key | Get it from |
|-----|------------|
| `COGNEE_API_KEY` + `COGNEE_BASE_URL` | [platform.cognee.ai/api-keys](https://platform.cognee.ai/api-keys) |
| `GEMINI_API_KEY` (if using `LLM_PROVIDER=gemini`) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `OPENAI_API_KEY` + `OPENAI_BASE_URL` (if using `LLM_PROVIDER=openai`, e.g. GLM-5 via AWS Bedrock Mantle) | your provider's console |

---

## 1. Backend Setup

```bash
# From project root
cd backend

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Now edit .env with your real API keys:
#   COGNEE_API_KEY=your_actual_cognee_key
#   COGNEE_BASE_URL=https://tenant-YOUR-ID.aws.cognee.ai
#   LLM_PROVIDER=gemini              # or "openai"
#   GEMINI_API_KEY=your_actual_gemini_key
#   OPENAI_API_KEY=your_actual_openai_compatible_key     # only needed if LLM_PROVIDER=openai
#   OPENAI_BASE_URL=https://bedrock-mantle.ap-south-1.api.aws/v1
#   OPENAI_MODEL=zai.glm-5
```

### Verify Backend

```bash
# From project root (not backend/)
python -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(dotenv_path=Path('backend/.env')); from backend.main import app; print('OK - App loaded')"
```

Expected output: `OK - App loaded`

---

## 2. Frontend Setup

```bash
# From project root
cd frontend

# Install dependencies
npm install

# .env.local already exists at frontend/.env.local with:
#   VITE_API_URL=http://localhost:8000
```

### Verify Frontend

```bash
npm run build
```

Expected: `✓ built in X.XXs`

---

## 3. Running the Full Stack

You need **two terminals** — one for backend, one for frontend.

### Terminal 1 — Backend

```bash
# From the project root (D:\Hackathon\Cognee_\digitan_twin)
# Activate the virtual environment
backend\.venv\Scripts\activate       # Windows
# source backend/.venv/bin/activate  # macOS/Linux

# Start the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Choosing the LLM provider

`LLM_PROVIDER` in `backend/.env` (`gemini` or `openai`) picks the default model. To override it
for a single run without editing `.env`, prefix the same `uvicorn` command with the env var —
a shell-exported variable always wins over `.env`:

```bash
LLM_PROVIDER=gemini uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # Google Gemini
LLM_PROVIDER=openai uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # GLM-5 via AWS Bedrock Mantle
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
VITE vX.X.X  ready in XXXms
➜  Local:   http://localhost:5173/
```

### Verify Backend is Working

Open a browser or use curl:

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","version":"1.0.0"}`

### Verify Portraits Endpoint

```bash
curl -I http://localhost:8000/portraits/feynman/portrait.svg
```

Expected: `HTTP/1.1 200 OK`

---

## 4. Seeding Source Material

Once the backend is running, ingest pre-configured source material for Feynman and Tesla:

```bash
# From project root, with backend server running
python -m backend.data.seed
```

This POSTs to `http://localhost:8000/ingest` for each source. Expected output:

```
[1/9] Ingesting: Feynman Lectures Vol I Ch1 (feynman)
  OK nodes_created=18, topics=...
[2/9] Ingesting: Nobel Lecture 1965 (feynman)
  OK nodes_created=15, topics=...
...
Seeding complete.
```

> If seeding fails, check that your `COGNEE_API_KEY` and `COGNEE_BASE_URL` are correct in `backend/.env`.

---

## 5. Testing the App

### Open the UI

Go to **http://localhost:5173** in your browser.

You should see:
- Left panel: "Choose a Mind" — Feynman, Tesla, Curie cards
- Center: Empty chat area with starter prompts
- Right panel: "Belief Contradictions" log

### Test Flow

1. **Click "Richard Feynman"** — the header shows "Talking to Richard Feynman"
2. **Click a starter prompt** (e.g., "What was your greatest mistake?")
3. **Wait** — the response loads with:
   - A **confidence badge** (Direct source / Extrapolated / Speculative)
   - **Citations** at the bottom (click to expand)
   - **Contradiction flag** if applicable

### API Test (if seed was successful)

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "figure_id": "feynman",
    "message": "What do you think about education?",
    "conversation_history": []
  }'
```

Expected: JSON with `response`, `citations`, `confidence`, `contradiction_flag`, `sources_used`

```bash
# Test graph endpoints
curl http://localhost:8000/figures
curl http://localhost:8000/topics/feynman
curl http://localhost:8000/contradictions/feynman
```

---

## 6. Project Structure

```
digital-twin/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── .env                       # API keys (you create this)
│   ├── .env.example               # Template for .env
│   ├── requirements.txt           # Python dependencies
│   ├── Procfile                   # Railway deployment
│   ├── railway.json               # Railway config
│   ├── routers/
│   │   ├── ingest.py              # POST /ingest  — source upload
│   │   ├── chat.py                # POST /chat    — conversation
│   │   └── graph.py               # GET /figures, /topics, /contradictions
│   ├── services/
│   │   ├── cognee_service.py      # Cognee Cloud memory graph
│   │   ├── llm_service.py         # LLM prompt + response (Gemini or OpenAI-compatible)
│   │   └── parser_service.py      # PDF/URL/text chunking
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   └── data/
│       ├── seed.py                # Source pre-ingestion script
│       └── figures/               # Portrait SVGs
│           ├── feynman/portrait.svg
│           ├── tesla/portrait.svg
│           └── curie/portrait.svg
│
├── frontend/
│   ├── .env.local                 # VITE_API_URL setting
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── vercel.json                # Vercel SPA rewrite
│   └── src/
│       ├── main.tsx               # React entry point
│       ├── App.tsx                # Main layout (3 panels)
│       ├── components/
│       │   ├── FigureSelector.tsx # Left sidebar — figure cards
│       │   ├── ChatWindow.tsx     # Center — chat UI
│       │   ├── CitationCard.tsx   # Expandable source citations
│       │   ├── ConfidenceBadge.tsx# Direct/Extrapolated/Speculative
│       │   └── ContradictionLog.tsx# Right sidebar — tension display
│       ├── hooks/
│       │   ├── useChat.ts         # Chat state management
│       │   └── useFigure.ts       # Topics + contradictions fetch
│       ├── api/
│       │   └── client.ts          # Axios API client
│       └── types/
│           └── index.ts           # TypeScript interfaces
│
└── README.md                      # Project overview
```

---

## 7. Common Issues

| Issue | Fix |
|-------|-----|
| `GEMINI_API_KEY is not set` | You're on `LLM_PROVIDER=gemini` — edit `backend/.env` with your real Gemini key |
| `OPENAI_API_KEY and OPENAI_BASE_URL must be set` | You're on `LLM_PROVIDER=openai` — edit `backend/.env` with your provider key + base URL |
| `Cognee ingestion failed` | Verify `COGNEE_API_KEY` and `COGNEE_BASE_URL` in `.env` |
| Frontend can't reach backend | Check `frontend/.env.local` has `VITE_API_URL=http://localhost:8000` |
| CORS errors in browser | Make sure backend is running on port 8000 |
| Seeding fails with timeout | Some URLs may be slow. Increase `timeout=60` in seed.py or try individual sources |
| `ModuleNotFoundError: No module named 'backend'` | Run commands from the **project root** (`digital-twin/`), not from `backend/` |

---

## 8. Quick One-Command Check

Run this from project root to verify everything:

```bash
# Check backend imports
python -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(dotenv_path=Path('backend/.env')); from backend.main import app; print('[OK] Backend imports')"

# Check frontend builds
cd frontend && npx tsc --noEmit && echo "[OK] Frontend TypeScript" && cd ..
```

Both should print `[OK]`.
