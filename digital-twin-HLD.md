# Dead People's Digital Twin — High Level Design (HLD)

> **Hackathon:** WeMakeDevs × Cognee — "The Hangover Part AI: Where's My Context?"
> **Track:** Best Use of Cognee Cloud (iPhone 17 prize)
> **Team Size:** 2
> **Stack:** FastAPI · React + TypeScript · Cognee Cloud · Claude API · Railway · Vercel

---

## 1. Problem Statement

Existing "talk to historical figures" AI tools are fundamentally broken — they hallucinate responses, invent quotes, and present fiction as fact. There is no grounding, no citation, no acknowledgment of contradictions in a person's evolving worldview.

The real problem: **a human's beliefs are a graph, not a document.** They contradict themselves. They evolve over decades. They have strong opinions on some topics and vague hunches on others. Flat RAG over PDFs loses all of this structure.

---

## 2. Solution Overview

A source-grounded memory system that ingests everything a historical figure ever wrote, said, or published — and builds a **hybrid graph-vector knowledge store** of their actual documented worldview using Cognee Cloud.

Users converse with the figure in natural language. Every response is:
- Grounded in real, ingested source material
- Cited with exact source, year, and document
- Honest about contradictions across time
- Transparent when extrapolating vs directly quoting

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + TS)                    │
│                                                                 │
│   ┌──────────────┐   ┌────────────────────┐   ┌─────────────┐  │
│   │ Figure       │   │ Chat Interface     │   │Contradiction│  │
│   │ Selector     │   │                    │   │Log Panel    │  │
│   │ + Topic Map  │   │ Messages           │   │             │  │
│   │              │   │ Citation Cards     │   │Timeline of  │  │
│   │ Feynman      │   │ Confidence Badge   │   │belief shifts│  │
│   │ Tesla        │   │ Source Drawer      │   │             │  │
│   │ Curie        │   │                    │   │             │  │
│   └──────────────┘   └────────────────────┘   └─────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS REST
┌──────────────────────────────▼──────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│                                                                 │
│  ┌─────────────────┐   ┌──────────────────┐  ┌──────────────┐  │
│  │  Ingest Router  │   │  Chat Router     │  │ Graph Router │  │
│  │  POST /ingest   │   │  POST /chat      │  │ GET /topics  │  │
│  │                 │   │                  │  │ GET /contra  │  │
│  │  - PDF parser   │   │  - Prompt builder│  │ -dictions    │  │
│  │  - URL scraper  │   │  - Claude caller │  │              │  │
│  │  - Text chunker │   │  - Citation      │  │              │  │
│  │  - Metadata tag │   │    extractor     │  │              │  │
│  └────────┬────────┘   └────────┬─────────┘  └──────┬───────┘  │
│           │                    │                    │           │
│  ┌────────▼────────────────────▼────────────────────▼────────┐  │
│  │                    Service Layer                          │  │
│  │   CogneeService · LLMService · ParserService             │  │
│  └────────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────┘
                                │ Cognee Python SDK
┌───────────────────────────────▼─────────────────────────────────┐
│                        COGNEE CLOUD                             │
│                                                                 │
│   remember()  →  Ingests source text into knowledge graph       │
│   recall()    →  Graph traversal + semantic vector search       │
│   improve()   →  Re-weights nodes, surfaces contradictions      │
│   forget()    →  Removes disputed or misattributed sources      │
│                                                                 │
│   One isolated dataset per figure (feynman / tesla / curie)     │
└─────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      CLAUDE API (Anthropic)                     │
│                                                                 │
│   Receives: figure persona + cognee recall results              │
│             + contradiction data + conversation history         │
│   Produces: grounded response in figure's voice + citations     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow

### 4.1 Ingestion Flow

```
Source Material (PDF / URL / Text)
        │
        ▼
ParserService
  - Extract raw text
  - Chunk into ~500 token segments
  - Tag each chunk with: {figure_id, source_title, year, doc_type}
        │
        ▼
CogneeService.ingest_source()
  - Prepend metadata tags to each chunk
  - Call cognee.remember(chunk, dataset_name=figure_id)
  - Cognee builds: vector embeddings + graph nodes + edges
        │
        ▼
Cognee Cloud Knowledge Graph
  - Nodes: concepts, opinions, events, people
  - Edges: relationships, contradictions, temporal evolution
  - Metadata: source, year, confidence level
```

### 4.2 Chat Flow

```
User message ("What did Feynman think about AI?")
        │
        ▼
POST /chat  {figure_id, message, conversation_history}
        │
        ▼
CogneeService.query_figure()
  - cognee.recall(question, dataset_name=figure_id)
  - Returns: relevant graph nodes + source citations
        │
        ▼
CogneeService.get_contradictions()
  - cognee.improve(dataset_name=figure_id)
  - cognee.recall("contradictions about [topic]")
        │
        ▼
LLMService.build_prompt()
  - System: figure persona + strict grounding rules
  - Context: cognee recall results + contradiction data
  - History: last N conversation turns
        │
        ▼
Claude API
  - Responds in figure's voice
  - Cites sources inline
  - Surfaces contradictions honestly
  - Flags when extrapolating
        │
        ▼
Response to Frontend
  {
    response: string,
    citations: [{quote, source, year, relevance_score}],
    sources_used: number,
    confidence: "direct" | "extrapolated" | "speculative"
  }
```

---

## 5. API Contract

### POST `/ingest`
```json
Request:
{
  "figure_id": "feynman",
  "source_type": "pdf" | "url" | "text",
  "content": "<base64 or string or url>",
  "metadata": {
    "title": "Surely You're Joking Mr. Feynman",
    "year": 1985,
    "doc_type": "book" | "interview" | "lecture" | "letter"
  }
}

Response:
{
  "status": "success",
  "nodes_created": 142,
  "topics_detected": ["physics", "education", "government"],
  "processing_time_ms": 3200
}
```

### POST `/chat`
```json
Request:
{
  "figure_id": "feynman",
  "message": "What do you think about AI replacing scientists?",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

Response:
{
  "response": "I'd be skeptical of any system that produces answers without...",
  "citations": [
    {
      "quote": "original source fragment",
      "source": "Nobel Lecture 1965",
      "year": 1965,
      "doc_type": "lecture",
      "relevance_score": 0.94
    }
  ],
  "sources_used": 4,
  "confidence": "direct",
  "contradiction_flag": false
}
```

### GET `/contradictions/{figure_id}`
```json
Response:
{
  "contradictions": [
    {
      "topic": "collaboration vs solo work",
      "statement_a": {
        "content": "Science is best pursued in solitude...",
        "source": "Century Magazine 1892",
        "year": 1892
      },
      "statement_b": {
        "content": "Edison's team approach produced remarkable results...",
        "source": "My Inventions 1919",
        "year": 1919
      },
      "tension_score": 0.87,
      "resolution": "unresolved" | "evolved" | "context_dependent"
    }
  ]
}
```

### GET `/topics/{figure_id}`
```json
Response:
{
  "topics": [
    { "name": "Quantum Mechanics", "strength": 0.95, "source_count": 23 },
    { "name": "Education Reform", "strength": 0.78, "source_count": 11 },
    { "name": "Government & NASA", "strength": 0.45, "source_count": 4 }
  ]
}
```

### DELETE `/source`
```json
Request:
{
  "figure_id": "feynman",
  "source_title": "disputed_interview_1990"
}

Response:
{
  "status": "forgotten",
  "nodes_removed": 18
}
```

---

## 6. Core Services

### CogneeService
Owns all interactions with Cognee Cloud. Each figure gets an isolated dataset to prevent cross-figure contamination.

```python
class CogneeService:
    async def ingest_source(figure_id, content, metadata)
      # Tags content with figure/source metadata
      # Calls cognee.remember(tagged_content, dataset_name=figure_id)

    async def query_figure(figure_id, question)
      # Calls cognee.recall(question, dataset_name=figure_id)
      # Returns graph nodes + citations

    async def get_contradictions(figure_id)
      # Calls cognee.improve(dataset_name=figure_id)
      # Queries for tension nodes in the graph

    async def forget_source(figure_id, source_title)
      # Calls cognee.forget(dataset=f"{figure_id}_{source_title}")
```

### LLMService
Builds the system prompt and calls Claude. The prompt is the critical piece — it enforces grounding and citation behavior.

```
SYSTEM PROMPT RULES:
1. Only express opinions grounded in provided memory context
2. Every claim must cite a specific source from context
3. Surface contradictions honestly — never hide belief evolution
4. When extrapolating, explicitly flag it as such
5. Never invent quotes — paraphrase with attribution if unsure
6. Cite sources naturally inline: "In my 1965 Nobel lecture..."
```

### ParserService
Handles raw source ingestion: PDF text extraction, URL scraping, plain text chunking. Outputs tagged chunks ready for Cognee ingestion.

---

## 7. Frontend Component Tree

```
App
├── FigureSelector
│   ├── FigureCard (Feynman / Tesla / Curie)
│   └── TopicMap (D3 bubble chart of belief clusters)
│
├── ChatWindow
│   ├── MessageList
│   │   ├── UserMessage
│   │   └── AssistantMessage
│   │       ├── ResponseText
│   │       ├── CitationCards (expandable)
│   │       ├── ConfidenceBadge (direct / extrapolated)
│   │       └── SourceCount ("drawn from 4 sources")
│   └── MessageInput
│
└── ContradictionLog (right panel)
    ├── ContradictionCard
    │   ├── TopicLabel
    │   ├── StatementA (with source + year)
    │   ├── StatementB (with source + year)
    │   └── TensionMeter
    └── TimelineView (belief evolution over years)
```

---

## 8. Pre-Ingested Source Corpus

All sources are public domain (pre-1928 or openly licensed by institutions).

### Richard Feynman
| Source | Year | Type | Status |
|--------|------|------|--------|
| The Feynman Lectures on Physics | 1964 | Lecture | Free — Caltech |
| Surely You're Joking Mr. Feynman (excerpts) | 1985 | Book | Key passages |
| Nobel Prize Lecture | 1965 | Lecture | Public — Nobel Foundation |
| Challenger Commission Testimony | 1986 | Gov. Document | Public domain |
| Omni Magazine Interview | 1979 | Interview | Public |

### Nikola Tesla
| Source | Year | Type | Status |
|--------|------|------|--------|
| My Inventions (Autobiography) | 1919 | Book | Full public domain |
| The Problem of Increasing Human Energy | 1900 | Article | Public domain |
| A New System of Alternating Current Motors | 1888 | Paper | Public domain |
| Various Patent Descriptions | 1880s–1900s | Patents | Public domain |

---

## 9. Confidence Levels

Every response carries a confidence badge based on how the answer was generated:

| Level | Meaning | Display |
|-------|---------|---------|
| `direct` | Response drawn directly from ingested quotes | 🟢 Direct source |
| `extrapolated` | Reasoning from related beliefs in the graph | 🟡 Extrapolated |
| `speculative` | Topic not covered — AI reasoning from worldview patterns | 🔴 Speculative |

This transparency is a core differentiator. The system is honest about what it knows vs what it's inferring.

---

## 10. Folder Structure

```
digital-twin/
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── ingest.py
│   │   ├── chat.py
│   │   └── graph.py
│   ├── services/
│   │   ├── cognee_service.py
│   │   ├── llm_service.py
│   │   └── parser_service.py
│   ├── models/
│   │   └── schemas.py
│   ├── data/
│   │   └── figures/
│   │       ├── feynman/
│   │       └── tesla/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FigureSelector.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── CitationCard.tsx
│   │   │   ├── ContradictionLog.tsx
│   │   │   └── TopicMap.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   └── useFigure.ts
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

## 11. Deployment Architecture

```
Developer Machine
      │
      ├── git push → GitHub
      │
      ├── Backend → Railway (auto-deploy from /backend)
      │             FastAPI on port 8000
      │             ENV: COGNEE_API_KEY, ANTHROPIC_API_KEY
      │
      └── Frontend → Vercel (auto-deploy from /frontend)
                    React SPA
                    ENV: VITE_API_URL=https://your-app.railway.app
```

---

## 12. Work Split (2 People)

| Task | Owner |
|------|-------|
| Cognee Cloud setup + dataset isolation | Backend Dev |
| Ingest pipeline (PDF/URL/text parsing) | Backend Dev |
| `/chat` endpoint + Claude prompt engineering | Backend Dev |
| Contradiction detection via `improve()` | Backend Dev |
| `/topics` + `/contradictions` endpoints | Backend Dev |
| Railway deployment + env config | Backend Dev |
| React project scaffold + routing | Frontend Dev |
| FigureSelector + TopicMap component | Frontend Dev |
| ChatWindow + MessageList + CitationCards | Frontend Dev |
| ContradictionLog panel | Frontend Dev |
| API client + TypeScript types | Frontend Dev |
| Vercel deployment | Frontend Dev |
| Demo video recording | Both |
| Blog post (side track) | Both |
| Social posts (side track) | Both |

---

## 13. 7-Day Execution Plan

| Day | Backend | Frontend |
|-----|---------|----------|
| **Day 1** | Cognee Cloud setup, ingest Feynman corpus | Project scaffold, FigureSelector UI |
| **Day 2** | `/chat` endpoint + Claude prompt + citations | ChatWindow + CitationCards (mocked) |
| **Day 3** | Contradiction detection + `/contradictions` | ContradictionLog + TopicMap |
| **Day 4** | `/topics` endpoint, metadata tagging | Wire real API, replace all mocks |
| **Day 5** | Add Tesla corpus, edge case handling | Polish UI, loading states, errors |
| **Day 6** | Railway deploy, stress test, README | Vercel deploy, cross-browser test |
| **Day 7** | Blog post + OSS PR contributions | Demo video + social posts |

---

## 14. Judging Criteria Mapping

| Criterion | How This Project Scores |
|-----------|------------------------|
| **Potential Impact** | Genuine research/education utility — students, journalists, museums |
| **Creativity** | Source-grounded contradiction-surfacing twin — nothing like it exists |
| **Technical Excellence** | Graph traversal + vector search + citation extraction + confidence levels |
| **Best Use of Cognee** | All 4 APIs used meaningfully: remember/recall/improve/forget |
| **User Experience** | Single compelling UI — conversation + citations + contradiction log |
| **Presentation** | Demo: type wrong claim → AI cites contradiction from 1892. Instant impact. |

---

## 15. The 60-Second Demo Script

1. Open app — Feynman's face, topic bubbles visible
2. Ask: *"What did you think about education?"*
3. Response appears with inline citations — room sees it's not hallucinated
4. Ask: *"Did you ever contradict yourself on this?"*
5. Contradiction log lights up — 1950 vs 1975 views side by side
6. Ask something Feynman never addressed: *"What would you think about TikTok?"*
7. AI reasons from his documented beliefs on attention and shallow entertainment
8. Response flagged as 🟡 Extrapolated — transparent about the inference

**The moment that wins:** step 7. The AI doesn't invent an answer. It navigates the graph of what he actually valued and reasons from there. That's what Cognee's graph layer makes possible that flat RAG cannot.
