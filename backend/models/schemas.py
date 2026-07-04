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
    content: str  # base64 for pdf, url string, raw text, or whatsapp .txt content
    metadata: SourceMetadata
    whatsapp_sender_name: Optional[str] = None


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
    portrait_url: str = ""
    is_public: bool = False
    relationship: Optional[str] = None
    source_count: int = 0


class FiguresResponse(BaseModel):
    public: list[FigureInfo]
    personal: list[FigureInfo]


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


class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str


class GoogleAuthRequest(BaseModel):
    token: str
