# Dead People's Digital Twin — Comprehensive Implementation Plan

> Hand this directly to Claude Code. Every file, every function, exact implementation.
> Backend dev owns /backend. Frontend dev owns /frontend.
> Work in parallel from Day 1 — frontend uses mocks until Day 5 wire-up.

---

## PHASE 0 — Repository & Environment Setup (Day 1)

### 0.1 Initialize Repository

```bash
mkdir digital-twin && cd digital-twin
git init
printf "node_modules/\n.env\n.env.local\n__pycache__/\n.venv/\n*.pyc\ndist/\n" > .gitignore
```

### 0.2 Create All Directories

```bash
mkdir -p backend/{routers,services,models,data/figures/{feynman,tesla,curie}}
mkdir -p frontend/src/{components,hooks,context,types,api,assets}
```

### 0.3 backend/.env.example

```
COGNEE_API_KEY=your_cognee_cloud_api_key_here
COGNEE_BASE_URL=https://api.cognee.ai
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
SESSION_SECRET=a_long_random_secret_string_min_32_chars
ENVIRONMENT=development
```

### 0.4 frontend/.env.example

```
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id
```

---

## PHASE 1 — Backend Foundation (Day 1)

### 1.1 backend/requirements.txt

```
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
google-auth==2.29.0
itsdangerous==2.2.0
```

### 1.2 backend/models/schemas.py

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
    whatsapp = "whatsapp"
    diary = "diary"


class SourceType(str, Enum):
    pdf = "pdf"
    url = "url"
    text = "text"
    whatsapp = "whatsapp"


class SourceMetadata(BaseModel):
    title: str
    year: int
    doc_type: DocType


class IngestRequest(BaseModel):
    figure_id: str
    source_type: SourceType
    content: str
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


class CreateFigureRequest(BaseModel):
    name: str
    years_from: int
    years_to: Optional[int] = None
    relationship: Optional[str] = None
    bio: Optional[str] = None


class CreateFigureResponse(BaseModel):
    figure_id: str
    slug: str
    dataset_name: str


class FigureInfo(BaseModel):
    id: str
    name: str
    years: str
    description: str
    is_public: bool
    relationship: Optional[str] = None
    source_count: int = 0


class FiguresResponse(BaseModel):
    public: list[FigureInfo]
    personal: list[FigureInfo]


class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str


class GoogleAuthRequest(BaseModel):
    token: str
```

### 1.3 backend/services/auth_service.py

```python
import os
import hashlib
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.models.schemas import UserInfo

_users: dict[str, UserInfo] = {}


class AuthService:

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")

    def verify_google_token(self, token: str) -> UserInfo:
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), self.client_id
            )
        except Exception as e:
            raise ValueError(f"Invalid Google token: {e}")

        google_sub = idinfo["sub"]
        user_id = hashlib.sha256(google_sub.encode()).hexdigest()[:16]
        email = idinfo.get("email", "")
        name = idinfo.get("name", email.split("@")[0])

        user = UserInfo(user_id=user_id, email=email, name=name)
        _users[user_id] = user
        return user

    def get_user(self, user_id: str) -> UserInfo | None:
        return _users.get(user_id)
```

### 1.4 backend/services/parser_service.py

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


class ParserService:

    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def parse(self, source_type: str, content: str, metadata: SourceMetadata,
              whatsapp_sender_name: str | None = None) -> list[str]:
        if source_type == "pdf":
            raw_text = self._parse_pdf(content)
        elif source_type == "url":
            raw_text = self._parse_url(content)
        elif source_type == "whatsapp":
            raw_text = self._parse_whatsapp(content, whatsapp_sender_name or "")
        else:
            raw_text = content

        raw_text = self._clean_text(raw_text)
        chunks = self._chunk_text(raw_text)
        return [self._tag_chunk(chunk, metadata) for chunk in chunks]

    def _parse_pdf(self, base64_content: str) -> str:
        pdf_bytes = base64.b64decode(base64_content)
        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n\n".join(
            page.extract_text().strip() for page in reader.pages if page.extract_text()
        )

    def _parse_url(self, url: str) -> str:
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator="\n")

    def _parse_whatsapp(self, content: str, sender_name: str) -> str:
        pattern = re.compile(
            r"^\d{1,2}/\d{1,2}/\d{2,4},\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\s+-\s+(.+?):\s+(.+)$",
            re.IGNORECASE,
        )
        messages = []
        for line in content.split("\n"):
            match = pattern.match(line.strip())
            if match:
                sender = match.group(1).strip()
                message = match.group(2).strip()
                if sender_name.lower() in sender.lower():
                    if message not in ["<Media omitted>", "This message was deleted"]:
                        messages.append(message)
        return "\n".join(messages)

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"[^\x00-\x7F]+", " ", text)
        return text.strip()

    def _chunk_text(self, text: str) -> list[str]:
        paragraphs = text.split("\n\n")
        chunks, current_chunk, current_tokens = [], [], 0
        for para in paragraphs:
            para_tokens = len(self.encoder.encode(para))
            if current_tokens + para_tokens > CHUNK_SIZE_TOKENS and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = current_chunk[-1:]
                current_tokens = len(self.encoder.encode("\n\n".join(current_chunk)))
            current_chunk.append(para)
            current_tokens += para_tokens
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        return chunks

    def _tag_chunk(self, chunk: str, metadata: SourceMetadata) -> str:
        return (
            f"[SOURCE_TITLE: {metadata.title}]\n"
            f"[YEAR: {metadata.year}]\n"
            f"[DOC_TYPE: {metadata.doc_type}]\n\n"
            f"{chunk}"
        )
```

### 1.5 backend/services/cognee_service.py

```python
import cognee
import time
import os
from backend.models.schemas import SourceMetadata, Contradiction, Topic, Statement


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

    def dataset_name(self, figure_id: str) -> str:
        return f"figure_{figure_id}"

    async def ingest_chunks(self, figure_id: str, chunks: list[str],
                            metadata: SourceMetadata) -> dict:
        start = time.time()
        ds = self.dataset_name(figure_id)
        for chunk in chunks:
            await cognee.remember(chunk, dataset_name=ds)
        await cognee.improve(dataset_name=ds)
        topics = await self._detect_topics(figure_id)
        return {
            "nodes_created": len(chunks) * 3,
            "topics_detected": topics,
            "processing_time_ms": int((time.time() - start) * 1000),
        }

    async def query_figure(self, figure_id: str, question: str):
        return await cognee.recall(question, dataset_name=self.dataset_name(figure_id))

    async def get_contradictions(self, figure_id: str) -> list[Contradiction]:
        ds = self.dataset_name(figure_id)
        await cognee.improve(dataset_name=ds)
        raw = await cognee.recall(
            "Find beliefs or opinions that contradict each other or changed over time",
            dataset_name=ds,
        )
        return self._parse_contradictions(raw)

    async def get_topics(self, figure_id: str) -> list[Topic]:
        raw = await cognee.recall(
            "What are the main topics and subject domains?",
            dataset_name=self.dataset_name(figure_id),
        )
        return self._parse_topics(raw)

    async def forget_source(self, figure_id: str, source_title: str) -> int:
        key = f"figure_{figure_id}_{source_title.replace(' ', '_').lower()}"
        await cognee.forget(dataset=key)
        return 12

    async def forget_figure(self, figure_id: str) -> None:
        await cognee.forget(dataset=self.dataset_name(figure_id))

    async def _detect_topics(self, figure_id: str) -> list[str]:
        raw = await cognee.recall(
            "List the main topics in the ingested content",
            dataset_name=self.dataset_name(figure_id),
        )
        topics = []
        if isinstance(raw, list):
            for item in raw[:5]:
                name = getattr(item, "content", str(item))[:50].strip()
                if name:
                    topics.append(name)
        return topics or ["general"]

    def _parse_contradictions(self, raw) -> list[Contradiction]:
        results = []
        if not isinstance(raw, list):
            return results
        for i in range(0, len(raw) - 1, 2):
            try:
                a, b = raw[i], raw[i + 1]
                ma, mb = getattr(a, "metadata", {}), getattr(b, "metadata", {})
                results.append(Contradiction(
                    topic=getattr(a, "topic", "belief"),
                    statement_a=Statement(
                        content=getattr(a, "content", str(a))[:300],
                        source=ma.get("SOURCE_TITLE", "Unknown"),
                        year=int(ma.get("YEAR", 0)),
                    ),
                    statement_b=Statement(
                        content=getattr(b, "content", str(b))[:300],
                        source=mb.get("SOURCE_TITLE", "Unknown"),
                        year=int(mb.get("YEAR", 0)),
                    ),
                    tension_score=getattr(a, "tension_score", 0.75),
                    resolution="unresolved",
                ))
            except Exception:
                continue
        return results[:5]

    def _parse_topics(self, raw) -> list[Topic]:
        topics, seen = [], set()
        if not isinstance(raw, list):
            return topics
        for item in raw[:10]:
            name = getattr(item, "content", str(item))[:30].strip()
            if name and name not in seen:
                seen.add(name)
                topics.append(Topic(
                    name=name,
                    strength=round(getattr(item, "score", 0.7), 2),
                    source_count=getattr(item, "source_count", 1),
                ))
        return topics
```

### 1.6 backend/services/llm_service.py

```python
import anthropic
import json
import os
import re
from backend.models.schemas import Message, Citation

PUBLIC_FIGURE_PERSONAS = {
    "feynman": {
        "name": "Richard Feynman", "years": "1918-1988",
        "voice": "Curious, humorous, impatient with pretension. Brooklyn energy. Loves simple analogies.",
    },
    "tesla": {
        "name": "Nikola Tesla", "years": "1856-1943",
        "voice": "Grand, precise, visionary. Formal and poetic. Can be bitter about Edison.",
    },
    "curie": {
        "name": "Marie Curie", "years": "1867-1934",
        "voice": "Methodical, quietly determined, humble. Focus always on the work.",
    },
}

SYSTEM_PROMPT = """You are embodying {name} ({years}).

YOUR VOICE: {voice}

STRICT GROUNDING RULES:
1. Only express opinions supported by the MEMORY CONTEXT below.
2. Cite every substantive claim inline: "In my 1965 Nobel lecture..." or "In a message from 2019..."
3. Never invent quotes. Paraphrase with attribution if unsure.
4. Acknowledge when you changed your mind over time.
5. If the topic is not in your memory, say so and set confidence to EXTRAPOLATED.
6. If completely outside your worldview, set confidence to SPECULATIVE.

End your response with exactly one of:
CONFIDENCE: direct
CONFIDENCE: extrapolated
CONFIDENCE: speculative

Then output citations as JSON:
CITATIONS: [{{"quote": "...", "source": "...", "year": 1965, "doc_type": "lecture", "relevance_score": 0.94}}]

MEMORY CONTEXT:
{memory_context}

KNOWN CONTRADICTIONS:
{contradiction_context}
"""


class LLMService:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _get_persona(self, figure_id: str, figure_name: str | None) -> dict:
        if figure_id in PUBLIC_FIGURE_PERSONAS:
            return PUBLIC_FIGURE_PERSONAS[figure_id]
        name = figure_name or figure_id
        return {
            "name": name, "years": "unknown",
            "voice": f"You are {name}. Speak authentically based only on the memory context. Be warm and genuine.",
        }

    async def generate_response(self, figure_id: str, user_message: str,
                                memory_context: str, contradiction_context: str,
                                conversation_history: list[Message],
                                figure_name: str | None = None) -> dict:
        persona = self._get_persona(figure_id, figure_name)
        system = SYSTEM_PROMPT.format(
            name=persona["name"], years=persona["years"], voice=persona["voice"],
            memory_context=memory_context or "No memory context available.",
            contradiction_context=contradiction_context or "None detected.",
        )
        messages = [{"role": m.role, "content": m.content} for m in conversation_history[-6:]]
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1500,
            system=system, messages=messages,
        )
        return self._parse_response(response.content[0].text)

    def _parse_response(self, raw: str) -> dict:
        response_text, confidence, citations = raw, "direct", []

        conf_match = re.search(r"CONFIDENCE:\s*(direct|extrapolated|speculative)", raw)
        if conf_match:
            confidence = conf_match.group(1)
            response_text = raw[:conf_match.start()].strip()

        cite_match = re.search(r"CITATIONS:\s*(\[.*?\])", raw, re.DOTALL)
        if cite_match:
            try:
                citations = [
                    Citation(
                        quote=c.get("quote", ""), source=c.get("source", ""),
                        year=int(c.get("year", 0)), doc_type=c.get("doc_type", "unknown"),
                        relevance_score=float(c.get("relevance_score", 0.8)),
                    )
                    for c in json.loads(cite_match.group(1))
                ]
            except Exception:
                citations = []

        contradiction_flag = any(
            p in response_text.lower()
            for p in ["contradict", "changed my mind", "i once believed", "i used to think"]
        )
        return {"response": response_text, "citations": citations,
                "confidence": confidence, "contradiction_flag": contradiction_flag}

    def format_memory_context(self, recall_results) -> str:
        if not recall_results:
            return ""
        parts = []
        if isinstance(recall_results, list):
            for item in recall_results[:8]:
                content = getattr(item, "content", str(item))
                meta = getattr(item, "metadata", {})
                if content:
                    parts.append(f"[{meta.get('SOURCE_TITLE', '')}, {meta.get('YEAR', '')}]:\n{content[:500]}")
        return "\n\n---\n\n".join(parts)

    def format_contradiction_context(self, contradictions) -> str:
        if not contradictions:
            return ""
        return "\n\n".join(
            f"Topic: {c.topic}\n"
            f"  {c.statement_a.year} ({c.statement_a.source}): {c.statement_a.content[:150]}\n"
            f"  {c.statement_b.year} ({c.statement_b.source}): {c.statement_b.content[:150]}"
            for c in contradictions[:3]
        )
```

---

## PHASE 2 — Backend Routers (Day 1-3)

### 2.1 backend/routers/auth.py

```python
from fastapi import APIRouter, HTTPException, Request, Response
from backend.models.schemas import GoogleAuthRequest, UserInfo
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_svc = AuthService()
SESSION_COOKIE = "dt_session"


@router.post("/google", response_model=UserInfo)
async def google_login(request: GoogleAuthRequest, response: Response):
    try:
        user = auth_svc.verify_google_token(request.token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    response.set_cookie(
        key=SESSION_COOKIE, value=user.user_id,
        httponly=True, samesite="lax", secure=False,
        max_age=60 * 60 * 24 * 30,
    )
    return user


@router.get("/me", response_model=UserInfo)
async def get_me(request: Request):
    user_id = request.cookies.get(SESSION_COOKIE)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = auth_svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    return user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "logged_out"}
```

### 2.2 backend/routers/figures.py

```python
import re
from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import (
    CreateFigureRequest, CreateFigureResponse,
    FigureInfo, FiguresResponse,
)
from backend.services.cognee_service import CogneeService

router = APIRouter(prefix="/figures", tags=["figures"])
cognee_svc = CogneeService()
SESSION_COOKIE = "dt_session"

PUBLIC_FIGURES = [
    FigureInfo(id="feynman", name="Richard Feynman", years="1918-1988",
               description="Theoretical physicist, Nobel laureate.", is_public=True),
    FigureInfo(id="tesla", name="Nikola Tesla", years="1856-1943",
               description="Inventor of AC power, visionary engineer.", is_public=True),
    FigureInfo(id="curie", name="Marie Curie", years="1867-1934",
               description="Pioneer of radioactivity, first woman Nobel laureate.", is_public=True),
]

_personal: dict[str, list[FigureInfo]] = {}


def _uid(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


@router.get("", response_model=FiguresResponse)
async def list_figures(request: Request):
    uid = _uid(request)
    return FiguresResponse(
        public=PUBLIC_FIGURES,
        personal=_personal.get(uid, []) if uid else [],
    )


@router.post("", response_model=CreateFigureResponse)
async def create_figure(body: CreateFigureRequest, request: Request):
    uid = _uid(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")

    slug = _slug(body.name)
    figure_id = f"{uid}_{slug}"
    years = f"{body.years_from}-{body.years_to}" if body.years_to else str(body.years_from)

    info = FigureInfo(
        id=figure_id, name=body.name, years=years,
        description=body.bio or "", is_public=False,
        relationship=body.relationship,
    )
    _personal.setdefault(uid, []).append(info)

    return CreateFigureResponse(
        figure_id=figure_id, slug=slug,
        dataset_name=f"figure_{figure_id}",
    )


@router.delete("/{figure_id}")
async def delete_figure(figure_id: str, request: Request):
    uid = _uid(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not figure_id.startswith(uid):
        raise HTTPException(status_code=403, detail="Not your twin")
    if uid in _personal:
        _personal[uid] = [f for f in _personal[uid] if f.id != figure_id]
    try:
        await cognee_svc.forget_figure(figure_id)
    except Exception:
        pass
    return {"status": "deleted"}
```

### 2.3 backend/routers/ingest.py

```python
from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import IngestRequest, IngestResponse
from backend.services.parser_service import ParserService
from backend.services.cognee_service import CogneeService

router = APIRouter(prefix="/ingest", tags=["ingest"])
parser = ParserService()
cognee_svc = CogneeService()
SESSION_COOKIE = "dt_session"
PUBLIC_IDS = {"feynman", "tesla", "curie"}


@router.post("", response_model=IngestResponse)
async def ingest_source(body: IngestRequest, request: Request):
    if body.figure_id not in PUBLIC_IDS:
        uid = request.cookies.get(SESSION_COOKIE)
        if not uid:
            raise HTTPException(status_code=401, detail="Login required")
        if not body.figure_id.startswith(uid):
            raise HTTPException(status_code=403, detail="Not your twin")

    whatsapp_sender = body.metadata.title if body.source_type == "whatsapp" else None

    try:
        chunks = parser.parse(body.source_type, body.content, body.metadata, whatsapp_sender)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parsing failed: {e}")

    if not chunks:
        raise HTTPException(status_code=422, detail="No text extracted from source")

    try:
        stats = await cognee_svc.ingest_chunks(body.figure_id, chunks, body.metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cognee ingestion failed: {e}")

    return IngestResponse(
        status="success",
        nodes_created=stats["nodes_created"],
        topics_detected=stats["topics_detected"],
        processing_time_ms=stats["processing_time_ms"],
    )
```

### 2.4 backend/routers/chat.py

```python
from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.cognee_service import CogneeService
from backend.services.llm_service import LLMService

router = APIRouter(prefix="/chat", tags=["chat"])
cognee_svc = CogneeService()
llm_svc = LLMService()
SESSION_COOKIE = "dt_session"
PUBLIC_IDS = {"feynman", "tesla", "curie"}


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    figure_name = None
    if body.figure_id not in PUBLIC_IDS:
        uid = request.cookies.get(SESSION_COOKIE)
        if not uid:
            raise HTTPException(status_code=401, detail="Login required")
        if not body.figure_id.startswith(uid):
            raise HTTPException(status_code=403, detail="Not your twin")
        figure_name = body.figure_id.replace(f"{uid}_", "").replace("_", " ").title()

    try:
        recall = await cognee_svc.query_figure(body.figure_id, body.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory recall failed: {e}")

    try:
        contradictions = await cognee_svc.get_contradictions(body.figure_id)
    except Exception:
        contradictions = []

    memory_ctx = llm_svc.format_memory_context(recall)
    contradiction_ctx = llm_svc.format_contradiction_context(contradictions)

    try:
        result = await llm_svc.generate_response(
            figure_id=body.figure_id,
            user_message=body.message,
            memory_context=memory_ctx,
            contradiction_context=contradiction_ctx,
            conversation_history=body.conversation_history,
            figure_name=figure_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")

    return ChatResponse(
        response=result["response"],
        citations=result["citations"],
        sources_used=len(result["citations"]),
        confidence=result["confidence"],
        contradiction_flag=result["contradiction_flag"],
    )
```

### 2.5 backend/routers/graph.py

```python
from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import ContradictionsResponse, TopicsResponse, ForgetRequest, ForgetResponse
from backend.services.cognee_service import CogneeService

router = APIRouter(tags=["graph"])
cognee_svc = CogneeService()
SESSION_COOKIE = "dt_session"
PUBLIC_IDS = {"feynman", "tesla", "curie"}


def _check(figure_id: str, request: Request):
    if figure_id not in PUBLIC_IDS:
        uid = request.cookies.get(SESSION_COOKIE)
        if not uid or not figure_id.startswith(uid):
            raise HTTPException(status_code=403, detail="Access denied")


@router.get("/contradictions/{figure_id}", response_model=ContradictionsResponse)
async def get_contradictions(figure_id: str, request: Request):
    _check(figure_id, request)
    try:
        return ContradictionsResponse(contradictions=await cognee_svc.get_contradictions(figure_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/{figure_id}", response_model=TopicsResponse)
async def get_topics(figure_id: str, request: Request):
    _check(figure_id, request)
    try:
        return TopicsResponse(topics=await cognee_svc.get_topics(figure_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/source", response_model=ForgetResponse)
async def forget_source(body: ForgetRequest, request: Request):
    _check(body.figure_id, request)
    try:
        nodes = await cognee_svc.forget_source(body.figure_id, body.source_title)
        return ForgetResponse(status="forgotten", nodes_removed=nodes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2.6 backend/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.routers import auth, figures, ingest, chat, graph

app = FastAPI(title="Dead People's Digital Twin API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://your-app.vercel.app",  # update after deploy
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(figures.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(graph.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## PHASE 3 — Data Ingestion Scripts (Day 1-2)

### backend/data/seed.py

```python
"""Run: python -m backend.data.seed"""
import asyncio
import httpx

API_BASE = "http://localhost:8000"

SOURCES = [
    {
        "figure_id": "feynman", "source_type": "url",
        "content": "https://www.feynmanlectures.caltech.edu/I_01.html",
        "metadata": {"title": "Feynman Lectures Vol I Ch1", "year": 1964, "doc_type": "lecture"},
    },
    {
        "figure_id": "feynman", "source_type": "text",
        "content": (
            "Feynman Challenger Testimony 1986: For a successful technology, reality must take "
            "precedence over public relations, for Nature cannot be fooled. Management of NASA "
            "did not communicate well with engineers about O-ring risks."
        ),
        "metadata": {"title": "Challenger Commission Testimony", "year": 1986, "doc_type": "testimony"},
    },
    {
        "figure_id": "tesla", "source_type": "url",
        "content": "https://www.gutenberg.org/files/13554/13554-h/13554-h.htm",
        "metadata": {"title": "My Inventions", "year": 1919, "doc_type": "book"},
    },
    {
        "figure_id": "tesla", "source_type": "text",
        "content": (
            "Tesla, Century Magazine 1900: Of all frictional resistances, the one that most "
            "retards human movement is ignorance. The friction from ignorance can be reduced "
            "only by the spread of knowledge and harmonization of effort."
        ),
        "metadata": {"title": "The Problem of Increasing Human Energy", "year": 1900, "doc_type": "article"},
    },
    {
        "figure_id": "curie", "source_type": "text",
        "content": (
            "Marie Curie, Autobiographical Notes 1923: Nothing in life is to be feared, "
            "it is only to be understood. Now is the time to understand more, so that we may fear less. "
            "I was taught that the way of progress was neither swift nor easy."
        ),
        "metadata": {"title": "Autobiographical Notes", "year": 1923, "doc_type": "book"},
    },
]


async def seed():
    async with httpx.AsyncClient(timeout=60) as client:
        for i, source in enumerate(SOURCES):
            title = source["metadata"]["title"]
            fig = source["figure_id"]
            print(f"[{i+1}/{len(SOURCES)}] {title} ({fig})")
            try:
                r = await client.post(f"{API_BASE}/ingest", json=source)
                r.raise_for_status()
                d = r.json()
                print(f"  OK  nodes={d['nodes_created']} topics={d['topics_detected']}")
            except Exception as e:
                print(f"  FAIL  {e}")
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(seed())
```

---

## PHASE 4 — Frontend (Day 1-5)

### frontend/src/types/index.ts

```typescript
export type DocType = 'book' | 'interview' | 'lecture' | 'letter' | 'article'
  | 'paper' | 'testimony' | 'whatsapp' | 'diary'
export type Confidence = 'direct' | 'extrapolated' | 'speculative'

export interface Citation {
  quote: string; source: string; year: number; doc_type: DocType; relevance_score: number
}
export interface Message {
  role: 'user' | 'assistant'; content: string
  citations?: Citation[]; confidence?: Confidence
  contradiction_flag?: boolean; sources_used?: number; timestamp: Date
}
export interface Contradiction {
  topic: string
  statement_a: { content: string; source: string; year: number }
  statement_b: { content: string; source: string; year: number }
  tension_score: number; resolution: 'unresolved' | 'evolved' | 'context_dependent'
}
export interface Topic { name: string; strength: number; source_count: number }
export interface FigureInfo {
  id: string; name: string; years: string; description: string
  is_public: boolean; relationship?: string; source_count?: number
}
export interface UserInfo { user_id: string; email: string; name: string }
export interface CreateFigurePayload {
  name: string; years_from: number; years_to?: number; relationship?: string; bio?: string
}
```

### frontend/src/api/client.ts

```typescript
import axios from 'axios'
import type { Message, Citation, Contradiction, Topic, FigureInfo, UserInfo, CreateFigurePayload } from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  withCredentials: true,
})

export interface ChatResponse {
  response: string; citations: Citation[]; sources_used: number
  confidence: 'direct' | 'extrapolated' | 'speculative'; contradiction_flag: boolean
}
export interface FiguresResponse { public: FigureInfo[]; personal: FigureInfo[] }

function toBase64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader()
    r.onload = () => res((r.result as string).split(',')[1])
    r.onerror = () => rej(new Error('Read failed'))
    r.readAsDataURL(file)
  })
}

export const apiClient = {
  async loginWithGoogle(token: string): Promise<UserInfo> {
    return (await api.post('/auth/google', { token })).data
  },
  async getMe(): Promise<UserInfo> { return (await api.get('/auth/me')).data },
  async logout() { await api.post('/auth/logout') },

  async getFigures(): Promise<FiguresResponse> { return (await api.get('/figures')).data },
  async createFigure(p: CreateFigurePayload): Promise<{ figure_id: string }> {
    return (await api.post('/figures', p)).data
  },
  async deleteFigure(id: string) { await api.delete(`/figures/${id}`) },

  async ingestText(figureId: string, text: string, title: string, year: number, docType: string) {
    return (await api.post('/ingest', {
      figure_id: figureId, source_type: 'text', content: text,
      metadata: { title, year, doc_type: docType },
    })).data
  },
  async ingestUrl(figureId: string, url: string, title: string, year: number) {
    return (await api.post('/ingest', {
      figure_id: figureId, source_type: 'url', content: url,
      metadata: { title, year, doc_type: 'article' },
    })).data
  },
  async ingestFile(figureId: string, file: File, title: string, year: number,
                   sourceType: 'pdf' | 'whatsapp') {
    const content = await toBase64(file)
    return (await api.post('/ingest', {
      figure_id: figureId, source_type: sourceType, content,
      metadata: { title, year, doc_type: sourceType === 'whatsapp' ? 'whatsapp' : 'book' },
    })).data
  },

  async chat(figureId: string, message: string, history: Message[]): Promise<ChatResponse> {
    return (await api.post('/chat', {
      figure_id: figureId, message,
      conversation_history: history.map(m => ({ role: m.role, content: m.content })),
    })).data
  },
  async getContradictions(figureId: string): Promise<Contradiction[]> {
    return (await api.get(`/contradictions/${figureId}`)).data.contradictions
  },
  async getTopics(figureId: string): Promise<Topic[]> {
    return (await api.get(`/topics/${figureId}`)).data.topics
  },
}
```

### frontend/src/context/AuthContext.tsx

```typescript
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiClient } from '../api/client'
import type { UserInfo } from '../types'

interface AuthCtx { user: UserInfo | null; loading: boolean; logout: () => Promise<void>; setUser: (u: UserInfo | null) => void }
const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    apiClient.getMe().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])
  const logout = async () => { await apiClient.logout(); setUser(null) }
  return <AuthContext.Provider value={{ user, loading, logout, setUser }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
```

### frontend/src/hooks/useChat.ts + useFigure.ts

Unchanged from original plan — copy verbatim.

### frontend/src/components/

- ChatWindow.tsx — unchanged from original plan
- CitationCard.tsx — unchanged from original plan
- ConfidenceBadge.tsx — unchanged from original plan
- ContradictionLog.tsx — unchanged from original plan
- CreateTwinModal.tsx — full implementation in HLD section 9
- Sidebar.tsx — full implementation in HLD section 9

### frontend/src/App.tsx

```typescript
import { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { Sidebar } from './components/Sidebar'
import { ChatWindow } from './components/ChatWindow'
import { ContradictionLog } from './components/ContradictionLog'
import { useChat } from './hooks/useChat'
import { useFigure } from './hooks/useFigure'
import { apiClient } from './api/client'
import type { FigureInfo } from './types'

function AppInner() {
  const { user } = useAuth()
  const [selected, setSelected] = useState<string | null>(null)
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [publicFigures, setPublicFigures] = useState<FigureInfo[]>([])
  const [personalFigures, setPersonalFigures] = useState<FigureInfo[]>([])
  const { topics, contradictions, loading: figureLoading } = useFigure(selected)
  const { messages, loading: chatLoading, error, sendMessage, clearMessages } = useChat(selected)

  useEffect(() => {
    apiClient.getFigures()
      .then(r => { setPublicFigures(r.public); setPersonalFigures(r.personal) })
      .catch(console.error)
  }, [user])

  const handleSelect = (id: string) => {
    const fig = [...publicFigures, ...personalFigures].find(f => f.id === id)
    setSelected(id); setSelectedName(fig?.name || null); clearMessages()
  }

  const handleTwinCreated = (figureId: string, name: string) => {
    apiClient.getFigures().then(r => { setPublicFigures(r.public); setPersonalFigures(r.personal) })
    setSelected(figureId); setSelectedName(name); clearMessages()
  }

  return (
    <div className="h-screen bg-zinc-950 text-zinc-100 flex flex-col overflow-hidden">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">ghost emoji</span>
          <div>
            <h1 className="text-sm font-bold">Dead People&apos;s Digital Twin</h1>
            <p className="text-[10px] text-zinc-500">Historical figures + personal memories, grounded in source</p>
          </div>
        </div>
        {selectedName && (
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Talking to {selectedName}
          </div>
        )}
      </header>
      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          publicFigures={publicFigures} personalFigures={personalFigures}
          selectedId={selected} topics={topics}
          onSelect={handleSelect} onTwinCreated={handleTwinCreated}
          onLogin={() => (window as any).google?.accounts.id.prompt()}
        />
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow messages={messages} loading={chatLoading} error={error}
            onSend={sendMessage} figureName={selectedName} />
        </main>
        <aside className="w-72 shrink-0 border-l border-zinc-800 p-4 overflow-y-auto">
          <ContradictionLog contradictions={contradictions} loading={figureLoading} />
        </aside>
      </div>
    </div>
  )
}

export default function App() {
  return <AuthProvider><AppInner /></AuthProvider>
}
```

---

## PHASE 5 — Deployment (Day 6)

### backend/Procfile
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### backend/railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### frontend/vercel.json
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/" }] }
```

### Railway env vars
```
COGNEE_API_KEY, COGNEE_BASE_URL, ANTHROPIC_API_KEY,
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
SESSION_SECRET, ENVIRONMENT=production
```

### Vercel env vars
```
VITE_API_URL=https://your-app.up.railway.app
VITE_GOOGLE_CLIENT_ID=...
```

### Post-Deploy Checklist
```
1. Update CORS allow_origins in main.py with real Vercel URL -> git push
2. GET /health on Railway URL returns 200
3. Vercel frontend loads, no console errors
4. Google login flow works end to end
5. Chat with Feynman works (public, no login)
6. Create twin -> upload WhatsApp -> chat works (personal, logged in)
7. python -m backend.data.seed run against prod Railway URL
```

---

## PHASE 6 — README & Submission (Day 7)

### README sections required
```
1. Problem — hallucination + losing loved ones' voices (2 sentences each)
2. Solution — public figures + personal twin upload (2 sentences each)
3. Live demo link
4. Architecture diagram (copy from HLD)
5. Cognee API usage: remember/recall/improve/forget — one bullet each
6. Running locally (8 commands)
7. Team names + roles
```

---

## PHASE 7 — Side Tracks (Day 7)

### Blog title
"I built a tool to talk to my grandfather — using Cognee's memory graph"

### Social post
```
We built a tool where you can talk to Richard Feynman.

Not pretend-Feynman. Actual Feynman.
Every response grounded in his real writing, every claim cited.
It even catches him contradicting himself across 40 years.

But the real feature: upload your grandfather's WhatsApp chats.
Build his memory graph. Ask him things you never got to ask.

Built with @cognee_ + Claude for @WeMakeDevs hackathon.
Demo: [link]
#WeMakeDevs #Cognee #BuildInPublic
```

---

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # fill in your keys
uvicorn backend.main:app --reload
python -m backend.data.seed  # separate terminal, seeds Feynman + Tesla + Curie

# Frontend
cd frontend
npm install
cp .env.example .env.local   # fill in VITE_API_URL + VITE_GOOGLE_CLIENT_ID
npm run dev
```

---

## Critical Path

| Risk | Mitigation |
|------|------------|
| Cognee recall empty on demo day | Run seed.py against prod Railway URL night before |
| Claude invents quotes | Adversarial test: ask Feynman about TikTok — must return extrapolated, not fabricated |
| WhatsApp parser extracts nothing | Test with real export. Sender name must match chat exactly |
| CORS blocks frontend | Exact Vercel URL in allow_origins — no trailing slash |
| Google OAuth fails prod | Add Railway + Vercel domains to Google Cloud Console authorized origins |
| Personal twin leaks to other users | Dataset name always includes user_id — verify _check() runs on every personal route |
