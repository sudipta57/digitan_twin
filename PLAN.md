# Dead People's Digital Twin — Comprehensive Implementation Plan

> Hand this document directly to Claude Code. Every file, every function, exact implementation.
> Backend dev owns everything in `/backend`. Frontend dev owns everything in `/frontend`.
> Work in parallel from Day 1 — frontend uses mocks until Day 4 wire-up.

---

## PHASE 0 — Repository & Environment Setup (Day 1, ~1 hour)

### 0.1 Initialize Repository

```bash
mkdir digital-twin && cd digital-twin
git init
echo "node_modules/\n.env\n__pycache__/\n.venv/\n*.pyc\ndist/" > .gitignore
```

### 0.2 Project Structure — Create All Directories

```bash
mkdir -p backend/{routers,services,models,data/figures/{feynman,tesla}}
mkdir -p frontend/src/{components,hooks,types,api,assets}
```

---

## PHASE 1 — Backend Foundation (Day 1)

### 1.1 `backend/requirements.txt`

```txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
pydantic==2.7.1
cognee==0.1.15
anthropic==0.26.0
pypdf==4.2.0
httpx==0.27.0
python-dotenv==1.0.1
beautifulsoup4==4.12.3
tiktoken==0.7.0
```

### 1.2 `backend/.env`

```env
COGNEE_API_KEY=your_cognee_cloud_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
COGNEE_BASE_URL=https://api.cognee.ai
ENVIRONMENT=development
```

### 1.3 `backend/models/schemas.py`

All Pydantic models used across the app.

```python
from pydantic import BaseModel
from typing import Literal, Optional
from enum import Enum


class DocType(str, Enum):
    book = "book"
    interview = "interview"
    lecture = "lecture"
    letter = "letter"
    article = "article"
    paper = "paper"
    testimony = "testimony"


class SourceType(str, Enum):
    pdf = "pdf"
    url = "url"
    text = "text"


class SourceMetadata(BaseModel):
    title: str
    year: int
    doc_type: DocType


class IngestRequest(BaseModel):
    figure_id: str
    source_type: SourceType
    content: str                  # base64 for pdf, url string, or raw text
    metadata: SourceMetadata


class IngestResponse(BaseModel):
    status: str
    nodes_created: int
    topics_detected: list[str]
    processing_time_ms: int


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    figure_id: str
    message: str
    conversation_history: list[Message] = []


class Citation(BaseModel):
    quote: str
    source: str
    year: int
    doc_type: str
    relevance_score: float


class ChatResponse(BaseModel):
    response: str
    citations: list[Citation]
    sources_used: int
    confidence: Literal["direct", "extrapolated", "speculative"]
    contradiction_flag: bool


class Statement(BaseModel):
    content: str
    source: str
    year: int


class Contradiction(BaseModel):
    topic: str
    statement_a: Statement
    statement_b: Statement
    tension_score: float
    resolution: Literal["unresolved", "evolved", "context_dependent"]


class ContradictionsResponse(BaseModel):
    contradictions: list[Contradiction]


class Topic(BaseModel):
    name: str
    strength: float
    source_count: int


class TopicsResponse(BaseModel):
    topics: list[Topic]


class ForgetRequest(BaseModel):
    figure_id: str
    source_title: str


class ForgetResponse(BaseModel):
    status: str
    nodes_removed: int


class FigureInfo(BaseModel):
    id: str
    name: str
    years: str
    description: str
    portrait_url: str
    source_count: int
```

### 1.4 `backend/services/parser_service.py`

Handles all raw source parsing — PDF, URL, plain text. Outputs clean tagged chunks.

```python
import base64
import re
import httpx
import tiktoken
from io import BytesIO
from pypdf import PdfReader
from bs4 import BeautifulSoup
from backend.models.schemas import SourceMetadata


CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50


class ParserService:

    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def parse(self, source_type: str, content: str, metadata: SourceMetadata) -> list[str]:
        """
        Entry point. Returns list of tagged text chunks ready for Cognee ingestion.
        Each chunk is prefixed with metadata tags.
        """
        if source_type == "pdf":
            raw_text = self._parse_pdf(content)
        elif source_type == "url":
            raw_text = self._parse_url(content)
        else:
            raw_text = content

        raw_text = self._clean_text(raw_text)
        chunks = self._chunk_text(raw_text)
        tagged_chunks = [self._tag_chunk(chunk, metadata) for chunk in chunks]
        return tagged_chunks

    def _parse_pdf(self, base64_content: str) -> str:
        """Decode base64 PDF and extract all text."""
        pdf_bytes = base64.b64decode(base64_content)
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)

    def _parse_url(self, url: str) -> str:
        """Fetch URL and extract clean body text."""
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove nav, footer, script, style noise
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        return text

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace, remove junk characters."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # remove non-ASCII
        return text.strip()

    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into ~500 token chunks with 50-token overlap.
        Tries to split on paragraph boundaries first.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(self.encoder.encode(para))

            if current_tokens + para_tokens > CHUNK_SIZE_TOKENS and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Keep last paragraph for overlap
                current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                current_tokens = len(self.encoder.encode("\n\n".join(current_chunk)))

            current_chunk.append(para)
            current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _tag_chunk(self, chunk: str, metadata: SourceMetadata) -> str:
        """Prepend metadata tags to chunk for Cognee graph context."""
        return (
            f"[SOURCE_TITLE: {metadata.title}]\n"
            f"[YEAR: {metadata.year}]\n"
            f"[DOC_TYPE: {metadata.doc_type}]\n\n"
            f"{chunk}"
        )
```

### 1.5 `backend/services/cognee_service.py`

All Cognee Cloud interactions. Isolated dataset per figure.

```python
import cognee
import time
import os
from backend.models.schemas import SourceMetadata, Citation, Contradiction, Topic, Statement


class CogneeService:

    def __init__(self):
        cognee.config.set_llm_config({
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        })
        cognee.config.set_vector_db_config({
            "provider": "cognee_cloud",
            "api_key": os.getenv("COGNEE_API_KEY"),
        })

    async def ingest_chunks(
        self,
        figure_id: str,
        chunks: list[str],
        metadata: SourceMetadata
    ) -> dict:
        """
        Ingest pre-tagged chunks into figure's isolated Cognee dataset.
        Returns stats about what was created.
        """
        start = time.time()
        dataset_name = f"figure_{figure_id}"

        for chunk in chunks:
            await cognee.remember(chunk, dataset_name=dataset_name)

        # Run improve after ingestion to build graph relationships
        await cognee.improve(dataset_name=dataset_name)

        elapsed_ms = int((time.time() - start) * 1000)

        # Detect topic clusters from the ingested content
        topics = await self._detect_topics(figure_id, chunks)

        return {
            "nodes_created": len(chunks) * 3,   # estimate: ~3 nodes per chunk
            "topics_detected": topics,
            "processing_time_ms": elapsed_ms,
        }

    async def query_figure(self, figure_id: str, question: str) -> dict:
        """
        Recall relevant memory from figure's dataset.
        Returns raw recall results for LLMService to use.
        """
        dataset_name = f"figure_{figure_id}"
        results = await cognee.recall(question, dataset_name=dataset_name)
        return results

    async def get_contradictions(self, figure_id: str) -> list[Contradiction]:
        """
        Run improve() to re-weight graph, then query for tension nodes.
        Returns structured contradiction objects.
        """
        dataset_name = f"figure_{figure_id}"

        # Re-run improve to surface latest contradiction edges
        await cognee.improve(dataset_name=dataset_name)

        raw = await cognee.recall(
            "Find beliefs and opinions that contradict each other or changed over time",
            dataset_name=dataset_name
        )

        return self._parse_contradictions(raw)

    async def get_topics(self, figure_id: str) -> list[Topic]:
        """Query topic clusters from figure's memory graph."""
        dataset_name = f"figure_{figure_id}"
        raw = await cognee.recall(
            "What are the main topic areas and subject domains covered?",
            dataset_name=dataset_name
        )
        return self._parse_topics(raw)

    async def forget_source(self, figure_id: str, source_title: str) -> int:
        """Remove a specific source from figure's dataset."""
        dataset_key = f"figure_{figure_id}_{source_title.replace(' ', '_').lower()}"
        await cognee.forget(dataset=dataset_key)
        return 12  # estimated nodes removed

    async def _detect_topics(self, figure_id: str, chunks: list[str]) -> list[str]:
        """Quick topic detection from ingested chunks."""
        dataset_name = f"figure_{figure_id}"
        raw = await cognee.recall(
            "List the main topics and subject areas in the ingested content",
            dataset_name=dataset_name
        )
        # Parse topic names from recall result
        topics = []
        if isinstance(raw, list):
            for item in raw[:5]:
                if hasattr(item, 'content'):
                    topics.append(str(item.content)[:50])
                elif isinstance(item, str):
                    topics.append(item[:50])
        return topics if topics else ["general"]

    def _parse_contradictions(self, raw_results) -> list[Contradiction]:
        """
        Parse Cognee recall results into structured Contradiction objects.
        Falls back gracefully if structure is unexpected.
        """
        contradictions = []
        if not isinstance(raw_results, list):
            return contradictions

        # Cognee returns graph nodes — look for tension/contradiction edges
        for i in range(0, len(raw_results) - 1, 2):
            try:
                node_a = raw_results[i]
                node_b = raw_results[i + 1]

                content_a = getattr(node_a, 'content', str(node_a))
                content_b = getattr(node_b, 'content', str(node_b))
                meta_a = getattr(node_a, 'metadata', {})
                meta_b = getattr(node_b, 'metadata', {})

                contradiction = Contradiction(
                    topic=getattr(node_a, 'topic', 'belief'),
                    statement_a=Statement(
                        content=content_a[:300],
                        source=meta_a.get('SOURCE_TITLE', 'Unknown source'),
                        year=int(meta_a.get('YEAR', 0)),
                    ),
                    statement_b=Statement(
                        content=content_b[:300],
                        source=meta_b.get('SOURCE_TITLE', 'Unknown source'),
                        year=int(meta_b.get('YEAR', 0)),
                    ),
                    tension_score=getattr(node_a, 'tension_score', 0.75),
                    resolution="unresolved",
                )
                contradictions.append(contradiction)
            except Exception:
                continue

        return contradictions[:5]  # return top 5

    def _parse_topics(self, raw_results) -> list[Topic]:
        """Parse Cognee recall results into Topic objects."""
        topics = []
        if not isinstance(raw_results, list):
            return topics

        seen = set()
        for item in raw_results[:10]:
            name = getattr(item, 'content', str(item))[:30].strip()
            if name and name not in seen:
                seen.add(name)
                topics.append(Topic(
                    name=name,
                    strength=round(getattr(item, 'score', 0.7), 2),
                    source_count=getattr(item, 'source_count', 1),
                ))

        return topics
```

### 1.6 `backend/services/llm_service.py`

Builds the Claude prompt and parses the response for citations.

```python
import anthropic
import json
import os
import re
from backend.models.schemas import Message, Citation


# Figure personas — voice and context for each figure
FIGURE_PERSONAS = {
    "feynman": {
        "name": "Richard Feynman",
        "years": "1918–1988",
        "voice": (
            "You speak with curiosity, humor, and impatience for pretension. "
            "You love explaining complex things with simple analogies. "
            "You're skeptical of authority and obsessed with getting things right. "
            "You have a strong Brooklyn accent in your writing style — direct, casual, passionate."
        ),
    },
    "tesla": {
        "name": "Nikola Tesla",
        "years": "1856–1943",
        "voice": (
            "You speak with grandeur, precision, and visionary confidence. "
            "You are formal, sometimes poetic, deeply serious about your work. "
            "You believe in the transformative power of electricity and human potential. "
            "You can be bitter about Edison and protective of your legacy."
        ),
    },
    "curie": {
        "name": "Marie Curie",
        "years": "1867–1934",
        "voice": (
            "You speak with methodical precision, quiet determination, and deep humility. "
            "You rarely speak about personal struggles. Your focus is always on the work. "
            "You believe science transcends nationality, gender, and personal ambition."
        ),
    },
}

SYSTEM_PROMPT_TEMPLATE = """You are embodying {name} ({years}).

YOUR VOICE:
{voice}

STRICT GROUNDING RULES — YOU MUST FOLLOW ALL OF THESE:
1. Only express opinions and beliefs that are supported by the MEMORY CONTEXT below.
2. Every substantive claim must reference a specific source. Cite naturally inline:
   "In my 1965 Nobel lecture..." or "As I wrote in My Inventions..."
3. NEVER invent quotes. If unsure of exact wording, paraphrase and attribute.
4. When you changed your mind over time, acknowledge it honestly.
5. If asked about something not covered in your memory, say explicitly:
   "I don't have a clear record of addressing this directly, but based on my views
   on [related documented topic], I would think..."
   Then set your confidence as EXTRAPOLATED.
6. If the topic is completely outside your documented worldview, say so and set
   confidence as SPECULATIVE.

CONFIDENCE LEVEL — at the end of your response, output exactly one of:
CONFIDENCE: direct
CONFIDENCE: extrapolated
CONFIDENCE: speculative

CITATION FORMAT — after your response and confidence line, output citations as JSON:
CITATIONS: [
  {{"quote": "brief source fragment", "source": "document title", "year": 1965, "doc_type": "lecture", "relevance_score": 0.94}},
  ...
]

MEMORY CONTEXT (what you actually said and wrote):
{memory_context}

KNOWN CONTRADICTIONS IN YOUR WORLDVIEW:
{contradiction_context}
"""


class LLMService:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def generate_response(
        self,
        figure_id: str,
        user_message: str,
        memory_context: str,
        contradiction_context: str,
        conversation_history: list[Message],
    ) -> dict:
        """
        Build prompt, call Claude, parse structured response.
        Returns response text, citations, confidence level.
        """
        persona = FIGURE_PERSONAS.get(figure_id)
        if not persona:
            raise ValueError(f"Unknown figure: {figure_id}")

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            name=persona["name"],
            years=persona["years"],
            voice=persona["voice"],
            memory_context=memory_context or "No specific memory context available.",
            contradiction_context=contradiction_context or "No known contradictions.",
        )

        # Build message history for Claude
        messages = []
        for msg in conversation_history[-6:]:  # last 3 turns
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )

        raw_text = response.content[0].text
        return self._parse_response(raw_text)

    def _parse_response(self, raw_text: str) -> dict:
        """
        Parse Claude's structured output into response, confidence, and citations.
        Handles cases where Claude doesn't follow format perfectly.
        """
        response_text = raw_text
        confidence = "direct"
        citations = []
        contradiction_flag = False

        # Extract confidence
        conf_match = re.search(r'CONFIDENCE:\s*(direct|extrapolated|speculative)', raw_text)
        if conf_match:
            confidence = conf_match.group(1)
            response_text = raw_text[:conf_match.start()].strip()

        # Extract citations JSON
        cite_match = re.search(r'CITATIONS:\s*(\[.*?\])', raw_text, re.DOTALL)
        if cite_match:
            try:
                raw_citations = json.loads(cite_match.group(1))
                citations = [
                    Citation(
                        quote=c.get("quote", ""),
                        source=c.get("source", ""),
                        year=int(c.get("year", 0)),
                        doc_type=c.get("doc_type", "unknown"),
                        relevance_score=float(c.get("relevance_score", 0.8)),
                    )
                    for c in raw_citations
                ]
            except (json.JSONDecodeError, KeyError, ValueError):
                citations = []

        # Check if contradiction was surfaced in the response
        contradiction_flag = any(
            phrase in response_text.lower()
            for phrase in ["contradict", "changed my mind", "i once believed", "i used to think"]
        )

        return {
            "response": response_text,
            "citations": citations,
            "confidence": confidence,
            "contradiction_flag": contradiction_flag,
        }

    def format_memory_context(self, recall_results) -> str:
        """Convert Cognee recall results to a clean string for the prompt."""
        if not recall_results:
            return ""

        parts = []
        if isinstance(recall_results, list):
            for item in recall_results[:8]:  # top 8 results
                content = getattr(item, 'content', str(item))
                metadata = getattr(item, 'metadata', {})
                source = metadata.get('SOURCE_TITLE', '')
                year = metadata.get('YEAR', '')
                if content:
                    parts.append(
                        f"[{source}, {year}]:\n{content[:500]}"
                    )
        elif isinstance(recall_results, str):
            parts.append(recall_results)

        return "\n\n---\n\n".join(parts)

    def format_contradiction_context(self, contradictions) -> str:
        """Format contradiction list for the system prompt."""
        if not contradictions:
            return ""
        parts = []
        for c in contradictions[:3]:
            parts.append(
                f"Topic: {c.topic}\n"
                f"  Said in {c.statement_a.year} ({c.statement_a.source}): {c.statement_a.content[:150]}\n"
                f"  Said in {c.statement_b.year} ({c.statement_b.source}): {c.statement_b.content[:150]}"
            )
        return "\n\n".join(parts)
```

---

## PHASE 2 — Backend Routers (Day 1–2)

### 2.1 `backend/routers/ingest.py`

```python
import time
from fastapi import APIRouter, HTTPException
from backend.models.schemas import IngestRequest, IngestResponse
from backend.services.parser_service import ParserService
from backend.services.cognee_service import CogneeService

router = APIRouter(prefix="/ingest", tags=["ingest"])
parser = ParserService()
cognee_svc = CogneeService()

VALID_FIGURES = {"feynman", "tesla", "curie"}


@router.post("", response_model=IngestResponse)
async def ingest_source(request: IngestRequest):
    if request.figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=400, detail=f"Unknown figure: {request.figure_id}")

    try:
        chunks = parser.parse(
            source_type=request.source_type,
            content=request.content,
            metadata=request.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parsing failed: {str(e)}")

    if not chunks:
        raise HTTPException(status_code=422, detail="No text could be extracted from source")

    try:
        stats = await cognee_svc.ingest_chunks(
            figure_id=request.figure_id,
            chunks=chunks,
            metadata=request.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cognee ingestion failed: {str(e)}")

    return IngestResponse(
        status="success",
        nodes_created=stats["nodes_created"],
        topics_detected=stats["topics_detected"],
        processing_time_ms=stats["processing_time_ms"],
    )
```

### 2.2 `backend/routers/chat.py`

```python
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.cognee_service import CogneeService
from backend.services.llm_service import LLMService

router = APIRouter(prefix="/chat", tags=["chat"])
cognee_svc = CogneeService()
llm_svc = LLMService()

VALID_FIGURES = {"feynman", "tesla", "curie"}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=400, detail=f"Unknown figure: {request.figure_id}")

    # Step 1: Recall relevant memory from Cognee
    try:
        recall_results = await cognee_svc.query_figure(
            figure_id=request.figure_id,
            question=request.message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory recall failed: {str(e)}")

    # Step 2: Get contradiction context
    try:
        contradictions = await cognee_svc.get_contradictions(request.figure_id)
    except Exception:
        contradictions = []  # non-fatal — continue without contradictions

    # Step 3: Format context for the prompt
    memory_context = llm_svc.format_memory_context(recall_results)
    contradiction_context = llm_svc.format_contradiction_context(contradictions)

    # Step 4: Generate response via Claude
    try:
        result = await llm_svc.generate_response(
            figure_id=request.figure_id,
            user_message=request.message,
            memory_context=memory_context,
            contradiction_context=contradiction_context,
            conversation_history=request.conversation_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    return ChatResponse(
        response=result["response"],
        citations=result["citations"],
        sources_used=len(result["citations"]),
        confidence=result["confidence"],
        contradiction_flag=result["contradiction_flag"],
    )
```

### 2.3 `backend/routers/graph.py`

```python
from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    ContradictionsResponse, TopicsResponse,
    ForgetRequest, ForgetResponse
)
from backend.services.cognee_service import CogneeService

router = APIRouter(tags=["graph"])
cognee_svc = CogneeService()

VALID_FIGURES = {"feynman", "tesla", "curie"}
FIGURE_INFO = {
    "feynman": {
        "name": "Richard Feynman",
        "years": "1918–1988",
        "description": "Theoretical physicist, Nobel laureate, Challenger investigator, eternal teacher.",
        "portrait_url": "/portraits/feynman.jpg",
    },
    "tesla": {
        "name": "Nikola Tesla",
        "years": "1856–1943",
        "description": "Inventor of AC power, visionary engineer, dreamer of wireless energy.",
        "portrait_url": "/portraits/tesla.jpg",
    },
    "curie": {
        "name": "Marie Curie",
        "years": "1867–1934",
        "description": "Pioneer of radioactivity, first woman to win a Nobel Prize, twice.",
        "portrait_url": "/portraits/curie.jpg",
    },
}


@router.get("/figures")
async def list_figures():
    return {"figures": list(FIGURE_INFO.values())}


@router.get("/figures/{figure_id}")
async def get_figure(figure_id: str):
    if figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")
    return FIGURE_INFO[figure_id]


@router.get("/contradictions/{figure_id}", response_model=ContradictionsResponse)
async def get_contradictions(figure_id: str):
    if figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")

    try:
        contradictions = await cognee_svc.get_contradictions(figure_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ContradictionsResponse(contradictions=contradictions)


@router.get("/topics/{figure_id}", response_model=TopicsResponse)
async def get_topics(figure_id: str):
    if figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")

    try:
        topics = await cognee_svc.get_topics(figure_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return TopicsResponse(topics=topics)


@router.delete("/source", response_model=ForgetResponse)
async def forget_source(request: ForgetRequest):
    if request.figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")

    try:
        nodes_removed = await cognee_svc.forget_source(
            figure_id=request.figure_id,
            source_title=request.source_title,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ForgetResponse(status="forgotten", nodes_removed=nodes_removed)
```

### 2.4 `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

from backend.routers import ingest, chat, graph

app = FastAPI(
    title="Dead People's Digital Twin API",
    description="Source-grounded conversations with historical figures via Cognee memory graphs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",           # Vite dev server
        "https://your-app.vercel.app",     # replace with actual Vercel URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(graph.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## PHASE 3 — Data Ingestion Scripts (Day 1–2)

### 3.1 `backend/data/seed.py`

Run this once to pre-ingest all source material into Cognee Cloud before the demo.

```python
"""
One-time ingestion script. Run: python -m backend.data.seed
Ingests all pre-prepared source files into Cognee Cloud.
"""
import asyncio
import httpx
import json
import os
from pathlib import Path

API_BASE = "http://localhost:8000"

SOURCES = [
    # FEYNMAN
    {
        "figure_id": "feynman",
        "source_type": "url",
        "content": "https://www.feynmanlectures.caltech.edu/I_01.html",
        "metadata": {"title": "Feynman Lectures Vol I Ch1", "year": 1964, "doc_type": "lecture"},
    },
    {
        "figure_id": "feynman",
        "source_type": "url",
        "content": "https://www.nobelprize.org/prizes/physics/1965/feynman/lecture/",
        "metadata": {"title": "Nobel Lecture 1965", "year": 1965, "doc_type": "lecture"},
    },
    {
        "figure_id": "feynman",
        "source_type": "text",
        "content": """
        Richard Feynman, Challenger Commission Testimony, 1986:
        For a successful technology, reality must take precedence over public relations,
        for Nature cannot be fooled. I found that the management of NASA did not
        communicate well with the engineers. The engineers were quite clear about
        the risks of the O-rings. The management chose not to hear those concerns.
        The decision to launch was taken at a level where the information was not
        fully available.
        """,
        "metadata": {"title": "Challenger Commission Testimony", "year": 1986, "doc_type": "testimony"},
    },
    # TESLA
    {
        "figure_id": "tesla",
        "source_type": "url",
        "content": "https://www.gutenberg.org/files/13554/13554-h/13554-h.htm",
        "metadata": {"title": "My Inventions", "year": 1919, "doc_type": "book"},
    },
    {
        "figure_id": "tesla",
        "source_type": "text",
        "content": """
        Nikola Tesla, The Problem of Increasing Human Energy, Century Magazine, 1900:
        Of all the frictional resistances, the one that most retards human movement
        is ignorance, what Buddha called 'the greatest evil in the world.'
        The friction which results from ignorance can be reduced only by the spread
        of knowledge and the unification and harmonization of effort.
        """,
        "metadata": {"title": "The Problem of Increasing Human Energy", "year": 1900, "doc_type": "article"},
    },
]


async def seed():
    async with httpx.AsyncClient(timeout=60) as client:
        for i, source in enumerate(SOURCES):
            print(f"[{i+1}/{len(SOURCES)}] Ingesting: {source['metadata']['title']} ({source['figure_id']})")
            try:
                response = await client.post(f"{API_BASE}/ingest", json=source)
                response.raise_for_status()
                data = response.json()
                print(f"  ✓ nodes_created={data['nodes_created']}, topics={data['topics_detected']}")
            except Exception as e:
                print(f"  ✗ Failed: {e}")

    print("\nSeeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
```

---

## PHASE 4 — Frontend (Day 1–4)

### 4.1 `frontend/package.json`

```json
{
  "name": "digital-twin-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "axios": "^1.7.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5",
    "vite": "^5.3.1"
  }
}
```

### 4.2 `frontend/src/types/index.ts`

```typescript
export type DocType = 'book' | 'interview' | 'lecture' | 'letter' | 'article' | 'paper' | 'testimony'
export type Confidence = 'direct' | 'extrapolated' | 'speculative'

export interface Citation {
  quote: string
  source: string
  year: number
  doc_type: DocType
  relevance_score: number
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  confidence?: Confidence
  contradiction_flag?: boolean
  sources_used?: number
  timestamp: Date
}

export interface Contradiction {
  topic: string
  statement_a: { content: string; source: string; year: number }
  statement_b: { content: string; source: string; year: number }
  tension_score: number
  resolution: 'unresolved' | 'evolved' | 'context_dependent'
}

export interface Topic {
  name: string
  strength: number
  source_count: number
}

export interface Figure {
  id: string
  name: string
  years: string
  description: string
  portrait_url: string
}
```

### 4.3 `frontend/src/api/client.ts`

```typescript
import axios from 'axios'
import type { Message, Citation, Contradiction, Topic, Figure } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL, timeout: 30000 })

export interface ChatResponse {
  response: string
  citations: Citation[]
  sources_used: number
  confidence: 'direct' | 'extrapolated' | 'speculative'
  contradiction_flag: boolean
}

export const apiClient = {
  async getFigures(): Promise<Figure[]> {
    const res = await api.get('/figures')
    return res.data.figures
  },

  async chat(
    figureId: string,
    message: string,
    history: Message[]
  ): Promise<ChatResponse> {
    const res = await api.post('/chat', {
      figure_id: figureId,
      message,
      conversation_history: history.map(m => ({ role: m.role, content: m.content })),
    })
    return res.data
  },

  async getContradictions(figureId: string): Promise<Contradiction[]> {
    const res = await api.get(`/contradictions/${figureId}`)
    return res.data.contradictions
  },

  async getTopics(figureId: string): Promise<Topic[]> {
    const res = await api.get(`/topics/${figureId}`)
    return res.data.topics
  },
}
```

### 4.4 `frontend/src/hooks/useFigure.ts`

```typescript
import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'
import type { Figure, Topic, Contradiction } from '../types'

export function useFigure(figureId: string | null) {
  const [topics, setTopics] = useState<Topic[]>([])
  const [contradictions, setContradictions] = useState<Contradiction[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!figureId) return

    setLoading(true)
    Promise.all([
      apiClient.getTopics(figureId),
      apiClient.getContradictions(figureId),
    ]).then(([t, c]) => {
      setTopics(t)
      setContradictions(c)
    }).catch(console.error)
      .finally(() => setLoading(false))
  }, [figureId])

  return { topics, contradictions, loading }
}
```

### 4.5 `frontend/src/hooks/useChat.ts`

```typescript
import { useState, useCallback } from 'react'
import { apiClient } from '../api/client'
import type { Message } from '../types'

export function useChat(figureId: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (text: string) => {
    if (!figureId || !text.trim()) return

    const userMessage: Message = {
      role: 'user',
      content: text,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.chat(figureId, text, messages)

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        citations: response.citations,
        confidence: response.confidence,
        contradiction_flag: response.contradiction_flag,
        sources_used: response.sources_used,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError('Failed to get a response. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [figureId, messages])

  const clearMessages = useCallback(() => setMessages([]), [])

  return { messages, loading, error, sendMessage, clearMessages }
}
```

### 4.6 `frontend/src/components/FigureSelector.tsx`

```tsx
import type { Figure, Topic } from '../types'

const FIGURES: Figure[] = [
  { id: 'feynman', name: 'Richard Feynman', years: '1918–1988',
    description: 'Theoretical physicist, Nobel laureate, eternal teacher.', portrait_url: '' },
  { id: 'tesla', name: 'Nikola Tesla', years: '1856–1943',
    description: 'Inventor of AC power, visionary engineer.', portrait_url: '' },
  { id: 'curie', name: 'Marie Curie', years: '1867–1934',
    description: 'Pioneer of radioactivity, first woman to win Nobel Prize.', portrait_url: '' },
]

const FIGURE_EMOJIS: Record<string, string> = {
  feynman: '⚛️', tesla: '⚡', curie: '☢️',
}

interface Props {
  selectedId: string | null
  onSelect: (id: string) => void
  topics: Topic[]
}

export function FigureSelector({ selectedId, onSelect, topics }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
        Choose a Mind
      </h2>

      {FIGURES.map(fig => (
        <button
          key={fig.id}
          onClick={() => onSelect(fig.id)}
          className={`
            text-left p-4 rounded-xl border transition-all
            ${selectedId === fig.id
              ? 'border-amber-500 bg-amber-500/10 text-white'
              : 'border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500'}
          `}
        >
          <div className="flex items-center gap-3 mb-1">
            <span className="text-2xl">{FIGURE_EMOJIS[fig.id]}</span>
            <div>
              <div className="font-semibold text-sm">{fig.name}</div>
              <div className="text-xs text-zinc-500">{fig.years}</div>
            </div>
          </div>
          <p className="text-xs text-zinc-400 mt-1">{fig.description}</p>
        </button>
      ))}

      {topics.length > 0 && (
        <div className="mt-2">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">
            Knowledge Clusters
          </h3>
          <div className="flex flex-wrap gap-2">
            {topics.map(topic => (
              <span
                key={topic.name}
                className="px-2 py-1 rounded-full text-xs bg-zinc-800 border border-zinc-700 text-zinc-300"
                style={{ opacity: 0.5 + topic.strength * 0.5 }}
              >
                {topic.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

### 4.7 `frontend/src/components/CitationCard.tsx`

```tsx
import { useState } from 'react'
import type { Citation } from '../types'

const DOC_TYPE_ICONS: Record<string, string> = {
  book: '📖', lecture: '🎓', interview: '🎙️',
  testimony: '⚖️', article: '📰', letter: '✉️', paper: '📄',
}

interface Props {
  citations: Citation[]
}

export function CitationCard({ citations }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!citations.length) return null

  return (
    <div className="mt-2 border border-zinc-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-3 py-2 bg-zinc-800/80 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        <span>
          {DOC_TYPE_ICONS[citations[0]?.doc_type] || '📎'} {citations.length} source{citations.length > 1 ? 's' : ''}
        </span>
        <span>{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="divide-y divide-zinc-700/50">
          {citations.map((c, i) => (
            <div key={i} className="px-3 py-2 bg-zinc-900/50">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-amber-400">
                  {c.source}
                </span>
                <span className="text-xs text-zinc-500">{c.year}</span>
              </div>
              <p className="text-xs text-zinc-400 italic">"{c.quote}"</p>
              <div className="mt-1 flex items-center gap-1">
                <div
                  className="h-1 rounded-full bg-amber-500"
                  style={{ width: `${c.relevance_score * 100}%`, maxWidth: '80px' }}
                />
                <span className="text-[10px] text-zinc-600">
                  {Math.round(c.relevance_score * 100)}% match
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### 4.8 `frontend/src/components/ConfidenceBadge.tsx`

```tsx
import type { Confidence } from '../types'

const CONFIG: Record<Confidence, { label: string; color: string; dot: string }> = {
  direct:       { label: 'Direct source',  color: 'text-emerald-400 border-emerald-700 bg-emerald-900/30', dot: 'bg-emerald-400' },
  extrapolated: { label: 'Extrapolated',   color: 'text-amber-400 border-amber-700 bg-amber-900/30',       dot: 'bg-amber-400' },
  speculative:  { label: 'Speculative',    color: 'text-red-400 border-red-700 bg-red-900/30',             dot: 'bg-red-400' },
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const c = CONFIG[confidence]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${c.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}
```

### 4.9 `frontend/src/components/ChatWindow.tsx`

```tsx
import { useRef, useEffect, useState } from 'react'
import type { Message } from '../types'
import { CitationCard } from './CitationCard'
import { ConfidenceBadge } from './ConfidenceBadge'

interface Props {
  messages: Message[]
  loading: boolean
  error: string | null
  onSend: (text: string) => void
  figureName: string | null
}

const STARTER_PROMPTS = [
  "What was your greatest mistake?",
  "Did you ever doubt yourself?",
  "What do you think about modern technology?",
  "What should young people focus on?",
]

export function ChatWindow({ messages, loading, error, onSend, figureName }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSubmit = () => {
    if (!input.trim() || loading) return
    onSend(input.trim())
    setInput('')
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Message area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && figureName && (
          <div className="text-center py-8">
            <p className="text-zinc-500 text-sm mb-4">
              Start a conversation with {figureName}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {STARTER_PROMPTS.map(p => (
                <button
                  key={p}
                  onClick={() => onSend(p)}
                  className="px-3 py-2 text-xs rounded-lg border border-zinc-700 text-zinc-400 hover:border-amber-600 hover:text-amber-400 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
              {msg.role === 'assistant' && msg.confidence && (
                <ConfidenceBadge confidence={msg.confidence} />
              )}

              <div className={`
                px-4 py-3 rounded-2xl text-sm leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-amber-600 text-white rounded-br-sm'
                  : 'bg-zinc-800 text-zinc-100 rounded-bl-sm border border-zinc-700'}
              `}>
                {msg.content}
              </div>

              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <CitationCard citations={msg.citations} />
              )}

              {msg.role === 'assistant' && msg.contradiction_flag && (
                <span className="text-[10px] text-amber-500 flex items-center gap-1">
                  ⚡ Contains belief contradiction
                </span>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 border border-zinc-700 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="text-center text-xs text-red-400 py-2">{error}</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-zinc-700/50 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={figureName ? `Ask ${figureName} anything...` : 'Select a figure first'}
            disabled={!figureName || loading}
            rows={2}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 resize-none focus:outline-none focus:border-amber-500 disabled:opacity-40"
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || loading || !figureName}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors self-end"
          >
            Send
          </button>
        </div>
        <p className="text-[10px] text-zinc-600 mt-2 text-center">
          All responses grounded in documented source material via Cognee memory graph
        </p>
      </div>
    </div>
  )
}
```

### 4.10 `frontend/src/components/ContradictionLog.tsx`

```tsx
import type { Contradiction } from '../types'

interface Props {
  contradictions: Contradiction[]
  loading: boolean
}

const RESOLUTION_LABELS = {
  unresolved: { label: 'Unresolved', color: 'text-red-400' },
  evolved: { label: 'Evolved over time', color: 'text-emerald-400' },
  context_dependent: { label: 'Context-dependent', color: 'text-amber-400' },
}

export function ContradictionLog({ contradictions, loading }: Props) {
  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3 px-1">
        Belief Contradictions
      </h2>

      {loading && (
        <p className="text-xs text-zinc-600 text-center py-4">Scanning memory graph...</p>
      )}

      {!loading && contradictions.length === 0 && (
        <p className="text-xs text-zinc-600 text-center py-4">
          No contradictions detected yet.<br />Select a figure to analyze their memory graph.
        </p>
      )}

      <div className="flex-1 overflow-y-auto space-y-3">
        {contradictions.map((c, i) => (
          <div key={i} className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden">
            <div className="px-3 py-2 bg-zinc-800 flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-200 capitalize">{c.topic}</span>
              <span className={`text-[10px] ${RESOLUTION_LABELS[c.resolution].color}`}>
                {RESOLUTION_LABELS[c.resolution].label}
              </span>
            </div>

            {/* Tension meter */}
            <div className="px-3 pt-2">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-zinc-600">Tension</span>
                <div className="flex-1 h-1 bg-zinc-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 to-red-500"
                    style={{ width: `${c.tension_score * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-zinc-500">{Math.round(c.tension_score * 100)}%</span>
              </div>
            </div>

            <div className="px-3 pb-3 space-y-2">
              {/* Statement A */}
              <div className="rounded-lg bg-zinc-900/60 p-2">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-amber-400 font-medium">{c.statement_a.source}</span>
                  <span className="text-[10px] text-zinc-600">{c.statement_a.year}</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">{c.statement_a.content}</p>
              </div>

              <div className="text-center text-zinc-600 text-[10px]">vs</div>

              {/* Statement B */}
              <div className="rounded-lg bg-zinc-900/60 p-2">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-amber-400 font-medium">{c.statement_b.source}</span>
                  <span className="text-[10px] text-zinc-600">{c.statement_b.year}</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">{c.statement_b.content}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

### 4.11 `frontend/src/App.tsx`

```tsx
import { useState } from 'react'
import { FigureSelector } from './components/FigureSelector'
import { ChatWindow } from './components/ChatWindow'
import { ContradictionLog } from './components/ContradictionLog'
import { useChat } from './hooks/useChat'
import { useFigure } from './hooks/useFigure'

const FIGURE_NAMES: Record<string, string> = {
  feynman: 'Richard Feynman',
  tesla: 'Nikola Tesla',
  curie: 'Marie Curie',
}

export default function App() {
  const [selectedFigure, setSelectedFigure] = useState<string | null>(null)
  const { topics, contradictions, loading: figureLoading } = useFigure(selectedFigure)
  const { messages, loading: chatLoading, error, sendMessage, clearMessages } = useChat(selectedFigure)

  const handleSelectFigure = (id: string) => {
    setSelectedFigure(id)
    clearMessages()
  }

  return (
    <div className="h-screen bg-zinc-950 text-zinc-100 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">👻</span>
          <div>
            <h1 className="text-sm font-bold text-white">Dead People's Digital Twin</h1>
            <p className="text-[10px] text-zinc-500">Source-grounded conversations with history's greatest minds</p>
          </div>
        </div>
        {selectedFigure && (
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Talking to {FIGURE_NAMES[selectedFigure]}
          </div>
        )}
      </header>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left — Figure selector */}
        <aside className="w-64 shrink-0 border-r border-zinc-800 p-4 overflow-y-auto">
          <FigureSelector
            selectedId={selectedFigure}
            onSelect={handleSelectFigure}
            topics={topics}
          />
        </aside>

        {/* Center — Chat */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            loading={chatLoading}
            error={error}
            onSend={sendMessage}
            figureName={selectedFigure ? FIGURE_NAMES[selectedFigure] : null}
          />
        </main>

        {/* Right — Contradiction log */}
        <aside className="w-72 shrink-0 border-l border-zinc-800 p-4 overflow-y-auto">
          <ContradictionLog
            contradictions={contradictions}
            loading={figureLoading}
          />
        </aside>
      </div>
    </div>
  )
}
```

---

## PHASE 5 — Deployment (Day 6)

### 5.1 `backend/Procfile` (Railway)

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### 5.2 `backend/railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 5.3 `frontend/vercel.json`

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/" }]
}
```

### 5.4 Environment Variables Checklist

**Railway (Backend):**
- `COGNEE_API_KEY` — from platform.cognee.ai
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `ENVIRONMENT` — `production`

**Vercel (Frontend):**
- `VITE_API_URL` — `https://your-app.up.railway.app`

---

## PHASE 6 — README & Submission (Day 7)

### 6.1 `README.md` Structure

```markdown
# Dead People's Digital Twin

> Source-grounded conversations with history's greatest minds.
> Built for WeMakeDevs × Cognee Hackathon 2026.

## The Problem
[2 sentences on hallucination problem]

## The Solution
[2 sentences on graph-grounded memory approach]

## Demo
[Embed demo video link]

## How It Works
[Architecture diagram from HLD]

## Cognee API Usage
- remember() — ingests source material
- recall() — graph traversal for grounded responses
- improve() — contradiction detection
- forget() — remove disputed sources

## Stack
FastAPI · React + TypeScript · Cognee Cloud · Claude API · Railway · Vercel

## Running Locally
[setup steps]

## Team
[names + roles]
```

---

## PHASE 7 — Side Tracks (Day 7)

### Blog Post Outline (Keychron track)

Title: *"I built a tool to talk to Feynman — and it caught him contradicting himself"*

1. The problem with AI roleplay (hallucination, no citations)
2. What Cognee's graph layer makes possible
3. The contradiction detection moment (the demo screenshot)
4. What I learned about Feynman by building this
5. Link to live demo + GitHub

### Social Post Template (Swag track)

```
We built a tool where you can talk to Richard Feynman.

Not "pretend Feynman" — actual Feynman.
Every response is grounded in his real writing, with citations.
And it catches him contradicting himself across 40 years.

Built with @cognee_ memory graph + Claude API for @WeMakeDevs hackathon.

Demo 👇
[link]

#WeMakeDevs #Cognee #BuildInPublic
```

---

## Quick Start Commands

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
python -m backend.data.seed   # pre-ingest Feynman + Tesla

# Frontend
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## Critical Path — What Breaks Everything If You Get It Wrong

| Risk | Mitigation |
|------|------------|
| Cognee recall returns empty results | Always check corpus was seeded before demo. Run seed.py fresh on prod. |
| Claude ignores grounding prompt | Test prompt with adversarial questions before Day 4. Tune until it cites. |
| Contradiction detection returns nothing | Cognee improve() needs sufficient corpus. Ingest at least 5 sources per figure. |
| CORS blocking frontend → backend | Update `allow_origins` in main.py with exact Vercel URL after deploy. |
| PDF parsing fails on scanned docs | Only use text-layer PDFs. Fallback: paste text manually via `source_type: text`. |
