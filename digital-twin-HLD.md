# Dead People's Digital Twin — High Level Design (HLD)

> **Hackathon:** WeMakeDevs × Cognee — "The Hangover Part AI: Where's My Context?"
> **Track:** Best Use of Cognee Cloud (iPhone 17 prize)
> **Team Size:** 2
> **Stack:** FastAPI · React + TypeScript · Cognee Cloud · Claude API · Railway · Vercel

---

## 1. Problem Statement

Existing "talk to historical figures" AI tools are fundamentally broken — they hallucinate responses, invent quotes, and present fiction as fact. There is no grounding, no citation, no acknowledgment of contradictions in a person's evolving worldview.

The real problem: **a human's beliefs are a graph, not a document.** They contradict themselves. They evolve over decades. They have strong opinions on some topics and vague hunches on others. Flat RAG over PDFs loses all of this structure.

This problem isn't limited to historical figures. People lose loved ones every day — grandparents, parents, friends — and with them, decades of wisdom, stories, and personality. There is no way to revisit a conversation you never had.

---

## 2. Solution Overview

A source-grounded memory system that ingests everything a person ever wrote, said, or published — and builds a **hybrid graph-vector knowledge store** of their actual documented worldview using Cognee Cloud.

Two modes:

**Public Figures** — pre-ingested historical figures (Feynman, Tesla, Curie) available to all users without login. Demonstrates the concept instantly.

**Personal Twins** — users upload their own source material (WhatsApp exports, letters, PDFs, diary entries, blog URLs) to build a private memory graph of someone they knew. Auth-gated. Completely private per user.

Every conversation response is:
- Grounded in real ingested source material
- Cited with exact source, year, and document
- Honest about contradictions across time
- Transparent when extrapolating vs directly quoting

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + TS)                        │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │ Figure Selector │  │   Chat Interface     │  │ Contradiction   │ │
│  │                 │  │                      │  │ Log Panel       │ │
│  │ Public Figures  │  │ Messages             │  │                 │ │
│  │ ─ Feynman       │  │ Citation Cards       │  │ Belief Timeline │ │
│  │ ─ Tesla         │  │ Confidence Badge     │  │ Tension Meter   │ │
│  │ ─ Curie         │  │ Source Drawer        │  │                 │ │
│  │                 │  │                      │  │                 │ │
│  │ My Twins        │  │                      │  │                 │ │
│  │ ─ [user list]   │  │                      │  │                 │ │
│  │ ─ + Create New  │  │                      │  │                 │ │
│  └─────────────────┘  └──────────────────────┘  └─────────────────┘ │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ HTTPS REST
┌─────────────────────────────────▼────────────────────────────────────┐
│                          BACKEND (FastAPI)                           │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │ Auth Router  │  │ Ingest Router│  │ Chat Router  │  │ Graph   │  │
│  │ POST /auth/  │  │ POST /ingest │  │ POST /chat   │  │ Router  │  │
│  │ google       │  │              │  │              │  │         │  │
│  │ POST /auth/  │  │ - PDF parser │  │ - Prompt     │  │ GET     │  │
│  │ logout       │  │ - URL scraper│  │   builder    │  │ /topics │  │
│  │ GET  /auth/  │  │ - TXT parser │  │ - LLM caller │  │         │  │
│  │ me           │  │ - Chunker    │  │ - Citation   │  │ GET     │  │
│  └──────────────┘  │ - Meta tagger│  │   extractor  │  │ /contra │  │
│                    └──────────────┘  └──────────────┘  │ -dicts  │  │
│                                                         └─────────┘  │
│  ┌──────────────┐                                                     │
│  │ Figure Router│                                                     │
│  │ GET  /figures│  (list public + user's private)                    │
│  │ POST /figures│  (create custom twin)                              │
│  │ DELETE /fig  │  (delete user's twin)                              │
│  └──────────────┘                                                     │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                        Service Layer                         │   │
│  │  CogneeService · LLMService · ParserService · AuthService    │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ Cognee Python SDK
┌──────────────────────────────────▼───────────────────────────────────┐
│                           COGNEE CLOUD                               │
│                                                                      │
│  remember()  →  Ingests source text into knowledge graph             │
│  recall()    →  Graph traversal + semantic vector search             │
│  improve()   →  Re-weights nodes, surfaces contradictions            │
│  forget()    →  Removes disputed or misattributed sources            │
│                                                                      │
│  Dataset naming:                                                     │
│  Public figures  →  figure_feynman / figure_tesla / figure_curie    │
│  Personal twins  →  figure_{user_id}_{slug}                         │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                         LLM (Claude API)                             │
│                                                                      │
│  Receives: figure persona + cognee recall results                    │
│            + contradiction data + conversation history               │
│  Produces: grounded response in figure's voice + citations           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. User Modes

### 4.1 Public Mode (No Login Required)
- Three pre-ingested historical figures available immediately
- Full chat + citations + contradiction log
- Zero friction — open the app and start talking

### 4.2 Personal Twin Mode (Login Required)
- User signs in via Google OAuth
- Creates a custom twin: name, years, relationship, short bio
- Uploads source material in any supported format
- Twin is private — only visible and accessible to that user
- Multiple twins supported per user (e.g. grandfather + grandmother)

---

## 5. Data Flow

### 5.1 Ingestion Flow (Public + Personal)

```
Source Material (PDF / TXT / URL / WhatsApp export / plain text)
        │
        ▼
ParserService
  - Detect format and route to correct parser
  - Extract raw text
  - Chunk into ~500 token segments
  - Tag each chunk: {figure_id, user_id, source_title, year, doc_type}
        │
        ▼
CogneeService.ingest_chunks()
  - Dataset name: figure_{figure_id} (public) or figure_{user_id}_{slug} (personal)
  - Call cognee.remember(tagged_chunk, dataset_name=...)
  - Cognee builds: vector embeddings + graph nodes + edges
        │
        ▼
Cognee Cloud Knowledge Graph
  - Nodes: concepts, opinions, events, people, memories
  - Edges: relationships, contradictions, temporal evolution
  - Metadata: source, year, doc_type, user_id
```

### 5.2 Chat Flow

```
User message + figure_id + user_id (if personal twin)
        │
        ▼
POST /chat → validate figure ownership (personal) or skip (public)
        │
        ▼
CogneeService.query_figure()
  - cognee.recall(question, dataset_name=correct_dataset)
  - Returns: relevant graph nodes + source citations
        │
        ▼
CogneeService.get_contradictions()
  - cognee.improve() then cognee.recall("contradictions...")
        │
        ▼
LLMService.generate_response()
  - System: figure persona + grounding rules
  - Context: recall results + contradiction data
  - History: last 6 conversation turns
        │
        ▼
Response → {response, citations, sources_used, confidence, contradiction_flag}
```

### 5.3 Personal Twin Creation Flow

```
User fills creation form → POST /figures
  {name, years, relationship, bio, is_public: false}
        │
        ▼
Backend generates figure_slug from name
Stores figure metadata in memory (in-process dict, MVP)
Returns figure_id = f"{user_id}_{slug}"
        │
        ▼
User uploads files → POST /ingest
  {figure_id, source_type, content, metadata}
  Repeats for each file/URL
        │
        ▼
Each upload → ParserService → CogneeService.ingest_chunks()
  dataset_name = f"figure_{user_id}_{slug}"
        │
        ▼
Twin ready — appears in user's "My Twins" sidebar list
```

---

## 6. API Contract

### Auth

#### POST `/auth/google`
```json
Request:  { "token": "<google_id_token>" }
Response: { "user_id": "abc123", "email": "user@gmail.com", "name": "Sudipta" }
```
Sets an HTTP-only session cookie on response.

#### GET `/auth/me`
```json
Response: { "user_id": "abc123", "email": "user@gmail.com", "name": "Sudipta" }
```
Returns 401 if not authenticated.

#### POST `/auth/logout`
```json
Response: { "status": "logged_out" }
```

---

### Figures

#### GET `/figures`
```json
Response:
{
  "public": [
    { "id": "feynman", "name": "Richard Feynman", "years": "1918–1988",
      "description": "...", "is_public": true }
  ],
  "personal": [
    { "id": "abc123_grandpa_rajan", "name": "Grandpa Rajan", "years": "1940–2021",
      "relationship": "Grandfather", "is_public": false, "source_count": 5 }
  ]
}
```
Personal list only returned if authenticated.

#### POST `/figures`
```json
Request:
{
  "name": "Grandpa Rajan",
  "years_from": 1940,
  "years_to": 2021,
  "relationship": "Grandfather",
  "bio": "Engineer from Kolkata, wrote letters every week"
}
Response:
{
  "figure_id": "abc123_grandpa_rajan",
  "slug": "grandpa_rajan",
  "dataset_name": "figure_abc123_grandpa_rajan"
}
```

#### DELETE `/figures/{figure_id}`
Deletes figure metadata and calls `cognee.forget()` on the dataset. Auth-gated — user can only delete their own.

---

### Ingest

#### POST `/ingest`
```json
Request:
{
  "figure_id": "abc123_grandpa_rajan",
  "source_type": "pdf" | "url" | "text" | "whatsapp",
  "content": "<base64 for pdf, url string, raw text, or whatsapp .txt content>",
  "metadata": {
    "title": "Letters to Father 1987",
    "year": 1987,
    "doc_type": "letter"
  }
}
Response:
{
  "status": "success",
  "nodes_created": 87,
  "topics_detected": ["family", "work", "advice"],
  "processing_time_ms": 2100
}
```

---

### Chat

#### POST `/chat`
```json
Request:
{
  "figure_id": "abc123_grandpa_rajan",
  "message": "What did you think about hard work?",
  "conversation_history": [...]
}
Response:
{
  "response": "Work is not something you do to survive...",
  "citations": [
    { "quote": "source fragment", "source": "Letter to Father 1987",
      "year": 1987, "doc_type": "letter", "relevance_score": 0.91 }
  ],
  "sources_used": 3,
  "confidence": "direct",
  "contradiction_flag": false
}
```

---

### Graph

#### GET `/contradictions/{figure_id}`
#### GET `/topics/{figure_id}`
#### DELETE `/source`
(Unchanged from original HLD — see Section 5 of original for full shapes)

---

## 7. Core Services

### AuthService
Handles Google OAuth token verification, session cookie management, and user identity resolution. Returns a `user_id` used as namespace prefix for all personal twin datasets.

### CogneeService
All Cognee Cloud interactions. Dataset isolation enforced by naming convention:
- Public: `figure_feynman`
- Personal: `figure_{user_id}_{slug}`

Ownership validated before any personal recall/ingest/forget operation.

### LLMService
Builds the Claude system prompt, calls the API, and parses the structured response (confidence level + citation JSON). Prompt grounding rules are non-negotiable — no weakening.

### ParserService
Routes by source type: PDF → pypdf, URL → httpx + BeautifulSoup, plain text → direct chunking, WhatsApp → custom `.txt` parser (strips timestamps and "sender:" prefixes, extracts message content only).

---

## 8. WhatsApp Export Parser

WhatsApp chat exports are `.txt` files with this format:
```
12/25/2021, 10:34 AM - Grandpa Rajan: Beta, always wake up early.
12/25/2021, 10:35 AM - You: Why dada?
12/25/2021, 10:36 AM - Grandpa Rajan: The world belongs to those who show up first.
```

Parser behavior:
- Accept the figure's name at parse time (provided by user during upload)
- Extract only messages sent by that name
- Strip timestamps and sender prefix
- Treat each message as a text chunk
- Tag with `doc_type: "whatsapp"` and `year` derived from timestamps

This makes personal twins incredibly easy to build — most people have years of WhatsApp history with loved ones.

---

## 9. Frontend Component Tree

```
App
├── AuthProvider (Google OAuth context)
│
├── Sidebar
│   ├── PublicFigures
│   │   └── FigureCard × 3 (Feynman / Tesla / Curie)
│   ├── MyTwins (auth-gated)
│   │   ├── PersonalFigureCard × N
│   │   └── CreateTwinButton → CreateTwinModal
│   └── LoginButton / UserAvatar
│
├── ChatWindow
│   ├── MessageList
│   │   ├── UserMessage
│   │   └── AssistantMessage
│   │       ├── ResponseText
│   │       ├── CitationCards (expandable)
│   │       ├── ConfidenceBadge (direct / extrapolated / speculative)
│   │       └── SourceCount
│   └── MessageInput
│
├── ContradictionLog (right panel)
│   ├── ContradictionCard × N
│   │   ├── TopicLabel
│   │   ├── StatementA + StatementB
│   │   └── TensionMeter
│   └── TimelineView
│
└── CreateTwinModal
    ├── Step 1: BasicInfoForm (name, years, relationship, bio)
    ├── Step 2: UploadForm
    │   ├── FileDropzone (PDF, TXT, WhatsApp .txt)
    │   ├── URLInput
    │   └── TextPasteArea
    └── Step 3: ProcessingView (progress per file)
```

---

## 10. Pre-Ingested Public Corpus

All sources public domain (pre-1928 or openly licensed).

### Richard Feynman
| Source | Year | Type |
|--------|------|------|
| Feynman Lectures Vol I Ch1 | 1964 | Lecture |
| Nobel Prize Lecture | 1965 | Lecture |
| Challenger Commission Testimony | 1986 | Testimony |
| Omni Magazine Interview | 1979 | Interview |

### Nikola Tesla
| Source | Year | Type |
|--------|------|------|
| My Inventions (Autobiography) | 1919 | Book |
| The Problem of Increasing Human Energy | 1900 | Article |
| A New System of Alternating Current Motors | 1888 | Paper |

### Marie Curie
| Source | Year | Type |
|--------|------|------|
| Autobiographical Notes | 1923 | Book |
| Nobel Lecture (Chemistry) | 1911 | Lecture |
| Pierre Curie (biography she wrote) | 1923 | Book |

---

## 11. Confidence Levels

| Level | Meaning | Badge |
|-------|---------|-------|
| `direct` | Drawn from ingested source material | 🟢 Direct source |
| `extrapolated` | Reasoned from related documented beliefs | 🟡 Extrapolated |
| `speculative` | Topic not in corpus — reasoning from worldview patterns | 🔴 Speculative |

---

## 12. Security & Privacy

- Personal twins are completely private — dataset names include `user_id`, inaccessible without a valid session
- All `/figures`, `/ingest`, `/chat` calls for personal twins validate session ownership before touching Cognee
- No cross-user data sharing possible at the dataset level
- Users can permanently delete their twin at any time via DELETE `/figures/{figure_id}` which calls `cognee.forget()`
- No raw uploaded files are stored server-side — content is parsed in memory and discarded after Cognee ingestion

---

## 13. Folder Structure

```
digital-twin/
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── figures.py
│   │   ├── ingest.py
│   │   ├── chat.py
│   │   └── graph.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── cognee_service.py
│   │   ├── llm_service.py
│   │   └── parser_service.py
│   ├── models/
│   │   └── schemas.py
│   ├── data/
│   │   └── figures/
│   │       ├── feynman/
│   │       ├── tesla/
│   │       └── curie/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── FigureCard.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── CitationCard.tsx
│   │   │   ├── ConfidenceBadge.tsx
│   │   │   ├── ContradictionLog.tsx
│   │   │   ├── CreateTwinModal.tsx
│   │   │   └── UploadForm.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   ├── useFigure.ts
│   │   │   └── useAuth.ts
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── README.md
```

---

## 14. Deployment Architecture

```
Developer Machine
      │
      ├── git push → GitHub
      │
      ├── Backend → Railway
      │   FastAPI on $PORT
      │   ENV: COGNEE_API_KEY, ANTHROPIC_API_KEY,
      │        GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
      │        SESSION_SECRET, ENVIRONMENT
      │
      └── Frontend → Vercel
          React SPA
          ENV: VITE_API_URL, VITE_GOOGLE_CLIENT_ID
```

---

## 15. Work Split (2 People)

| Task | Owner |
|------|-------|
| Cognee Cloud setup + dataset isolation | Backend Dev |
| Auth service (Google OAuth + sessions) | Backend Dev |
| Ingest pipeline (PDF/URL/text/WhatsApp) | Backend Dev |
| `/chat` endpoint + LLM prompt engineering | Backend Dev |
| Contradiction detection via `improve()` | Backend Dev |
| Figure management endpoints | Backend Dev |
| Railway deployment | Backend Dev |
| React scaffold + routing + AuthContext | Frontend Dev |
| Sidebar (public figures + My Twins list) | Frontend Dev |
| ChatWindow + CitationCards + ConfidenceBadge | Frontend Dev |
| CreateTwinModal (3-step flow) | Frontend Dev |
| UploadForm + file dropzone | Frontend Dev |
| ContradictionLog panel | Frontend Dev |
| Vercel deployment | Frontend Dev |
| Demo video | Both |
| Blog post | Both |
| Social posts | Both |

---

## 16. 7-Day Execution Plan

| Day | Backend | Frontend |
|-----|---------|----------|
| **Day 1** | Cognee setup, public figure ingest (Feynman+Tesla+Curie), `/health` | Scaffold, routing, Sidebar with public figures |
| **Day 2** | `/chat` + LLM prompt + citation parsing | ChatWindow + CitationCards + ConfidenceBadge (mocked) |
| **Day 3** | Google OAuth + sessions + figure ownership validation | AuthContext + LoginButton + CreateTwinModal Step 1 |
| **Day 4** | `/figures` CRUD + WhatsApp parser + personal ingest | UploadForm + CreateTwinModal Steps 2–3 + My Twins list |
| **Day 5** | Contradiction detection + `/topics` + edge case handling | ContradictionLog + wire all real API calls, replace mocks |
| **Day 6** | Railway deploy + CORS update + stress test | Vercel deploy + cross-browser test + loading/error states |
| **Day 7** | Blog post + OSS PR | Demo video + social posts |

---

## 17. Judging Criteria Mapping

| Criterion | How This Project Scores |
|-----------|------------------------|
| **Potential Impact** | Historians, students, journalists — AND grieving families who want to preserve a loved one's voice |
| **Creativity** | Only project combining source-grounded historical twins + personal memory upload |
| **Technical Excellence** | Graph traversal + vector search + WhatsApp parser + auth + citation extraction |
| **Best Use of Cognee** | All 4 APIs: remember/recall/improve/forget, across public and private isolated datasets |
| **User Experience** | Zero-friction public demo + emotional personal twin creation flow |
| **Presentation** | Demo arc: Feynman → "now upload your grandfather's WhatsApp" — room goes silent |

---

## 18. The 60-Second Demo Script

1. Open app — three historical figures visible, no login needed
2. Click Feynman → ask *"What did you think about education?"*
3. Response with inline citations — not hallucinated, room sees grounding
4. Ask *"Did you ever contradict yourself?"* — contradiction log lights up
5. Click **+ Create Twin** → fill name "Grandpa Rajan", years 1940–2021
6. Upload a WhatsApp `.txt` export — processing bar fills
7. Ask Grandpa Rajan: *"What do you think about hard work?"*
8. Response grounded in his actual WhatsApp messages, cited by date

**The moment that wins:** step 7–8. Someone just talked to their grandfather. That's not a hackathon demo. That's a product.
