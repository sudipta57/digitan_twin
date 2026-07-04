import json
import logging
import os
import re
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from backend.models.schemas import Message, Citation, Topic, Contradiction, Statement

logger = logging.getLogger(__name__)


FIGURE_PERSONAS = {
    "feynman": {
        "name": "Richard Feynman",
        "years": "1918-1988",
        "voice": (
            "You speak with curiosity, humor, and impatience for pretension. "
            "You love explaining complex things with simple analogies. "
            "You're skeptical of authority and obsessed with getting things right. "
            "You have a strong Brooklyn accent in your writing style — direct, casual, passionate."
        ),
    },
    "tesla": {
        "name": "Nikola Tesla",
        "years": "1856-1943",
        "voice": (
            "You speak with grandeur, precision, and visionary confidence. "
            "You are formal, sometimes poetic, deeply serious about your work. "
            "You believe in the transformative power of electricity and human potential. "
            "You can be bitter about Edison and protective of your legacy."
        ),
    },
    "curie": {
        "name": "Marie Curie",
        "years": "1867-1934",
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
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.openai_model = os.getenv("OPENAI_MODEL", "zai.glm-5")
        self._gemini_client = None
        self._openai_client = None
        active_model = self.openai_model if self.provider == "openai" else self.gemini_model
        logger.info(f"LLM provider={self.provider} model={active_model}")

    @property
    def gemini_client(self):
        if self._gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set in environment")
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    @property
    def openai_client(self):
        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            if not api_key or not base_url:
                raise ValueError("OPENAI_API_KEY and OPENAI_BASE_URL must be set in environment")
            self._openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self._openai_client

    def _get_persona(self, figure_id: str, figure_name: str | None,
                      relationship: str | None, bio: str | None) -> dict:
        persona = FIGURE_PERSONAS.get(figure_id)
        if persona:
            return persona

        name = figure_name or figure_id
        relationship_note = f" who was the user's {relationship}" if relationship else ""
        bio_note = f" Background: {bio}" if bio else ""
        return {
            "name": name,
            "years": "unknown",
            "voice": (
                f"You are {name}{relationship_note}. Speak authentically and warmly, "
                f"strictly based on the memory context provided below — never invent "
                f"personality traits or facts that aren't grounded in it.{bio_note}"
            ),
        }

    async def generate_response(
        self,
        figure_id: str,
        user_message: str,
        memory_context: str,
        contradiction_context: str,
        conversation_history: list[Message],
        figure_name: str | None = None,
        relationship: str | None = None,
        bio: str | None = None,
    ) -> dict:
        persona = self._get_persona(figure_id, figure_name, relationship, bio)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            name=persona["name"],
            years=persona["years"],
            voice=persona["voice"],
            memory_context=memory_context or "No specific memory context available.",
            contradiction_context=contradiction_context or "No known contradictions.",
        )

        if self.provider == "openai":
            raw_text = await self._generate_openai(system_prompt, user_message, conversation_history)
        else:
            raw_text = await self._generate_gemini(system_prompt, user_message, conversation_history)

        return self._parse_response(raw_text)

    async def _generate_gemini(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: list[Message],
    ) -> str:
        # Gemini only supports system_instruction for the first turn;
        # we pass conversation history as alternating user/model turns
        contents = []
        for msg in conversation_history[-6:]:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.content)],
            ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        ))

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1500,
        )

        response = await self.gemini_client.aio.models.generate_content(
            model=self.gemini_model,
            contents=contents,
            config=config,
        )

        return response.text

    async def _generate_openai(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: list[Message],
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-6:]:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        response = await self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            max_tokens=1500,
        )

        return response.choices[0].message.content

    def _parse_response(self, raw_text: str) -> dict:
        response_text = raw_text
        confidence = "direct"
        citations = []
        contradiction_flag = False

        conf_match = re.search(r"CONFIDENCE:\s*(direct|extrapolated|speculative)", raw_text)
        if conf_match:
            confidence = conf_match.group(1)
            response_text = raw_text[:conf_match.start()].strip()

        cite_match = re.search(r"CITATIONS:\s*(\[.*?\])", raw_text, re.DOTALL)
        if cite_match:
            try:
                raw_citations = json.loads(cite_match.group(1))
                citations = [
                    Citation(
                        quote=c.get("quote") or "",
                        source=c.get("source") or "",
                        year=int(c.get("year") or 0),
                        doc_type=c.get("doc_type") or "unknown",
                        relevance_score=float(c.get("relevance_score") if c.get("relevance_score") is not None else 0.8),
                    )
                    for c in raw_citations
                ]
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                citations = []

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

    def format_memory_context(self, recall_results: list[dict]) -> str:
        """recall_results are raw CHUNKS entries from cognee.recall — each chunk's
        text already carries our [SOURCE_TITLE]/[YEAR]/[DOC_TYPE] tags inline
        (see ParserService._tag_chunk), so no extra metadata lookup is needed."""
        if not recall_results:
            return ""
        parts = [chunk["text"][:800] for chunk in recall_results[:8] if chunk.get("text")]
        return "\n\n---\n\n".join(parts)

    def format_contradiction_context(self, contradictions) -> str:
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

    async def _generate_raw(self, system_prompt: str, user_message: str) -> str:
        if self.provider == "openai":
            return await self._generate_openai(system_prompt, user_message, [])
        return await self._generate_gemini(system_prompt, user_message, [])

    @staticmethod
    def _extract_json_array(raw_text: str) -> list:
        match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    async def extract_topics(self, chunks: list[str]) -> list[Topic]:
        """Cognee's recall API returns raw grounded text (see CogneeService._recall_chunks),
        not structured topic data — we ask our own LLM to summarize it into topics."""
        context = "\n\n---\n\n".join(chunks[:15])[:8000]
        raw = await self._generate_raw(
            "You analyze source material about a person and identify their main topics or "
            "subject areas. Return ONLY a JSON array, no prose, no markdown fences, in this exact "
            'shape: [{"name": "family", "strength": 0.8, "source_count": 3}]. "strength" is 0-1 '
            'relative importance, "source_count" is how many distinct chunks mention it. '
            "Return at most 8 topics.\n\nSOURCE MATERIAL:\n" + context,
            "Extract the topics now.",
        )
        topics = []
        for item in self._extract_json_array(raw)[:8]:
            try:
                topics.append(Topic(
                    name=str(item.get("name", "")).strip()[:30],
                    strength=round(float(item.get("strength", 0.7)), 2),
                    source_count=int(item.get("source_count", 1)),
                ))
            except (TypeError, ValueError):
                continue
        return [t for t in topics if t.name]

    async def extract_contradictions(self, chunks: list[str]) -> list[Contradiction]:
        """Same rationale as extract_topics — Cognee's recall doesn't expose contradiction
        pairs directly, so we ask our own LLM to find them in the grounded chunk text."""
        context = "\n\n---\n\n".join(chunks[:15])[:8000]
        raw = await self._generate_raw(
            "You analyze source material about a person (each chunk starts with "
            "[SOURCE_TITLE: ...] [YEAR: ...] [DOC_TYPE: ...] tags) to find beliefs or opinions "
            "that contradict each other or evolved over time. Return ONLY a JSON array, no prose, "
            'no markdown fences, in this exact shape: [{"topic": "hard work", '
            '"statement_a": {"content": "...", "source": "...", "year": 1987}, '
            '"statement_b": {"content": "...", "source": "...", "year": 1995}, '
            '"tension_score": 0.7}]. Use the SOURCE_TITLE and YEAR tags for "source" and "year". '
            "If there are no genuine contradictions, return []. Return at most 5.\n\n"
            "SOURCE MATERIAL:\n" + context,
            "Extract the contradictions now.",
        )
        contradictions = []
        for item in self._extract_json_array(raw)[:5]:
            try:
                contradictions.append(Contradiction(
                    topic=str(item.get("topic", "belief"))[:50],
                    statement_a=Statement(
                        content=str(item["statement_a"]["content"])[:300],
                        source=str(item["statement_a"].get("source", "Unknown"))[:100],
                        year=int(item["statement_a"].get("year", 0)),
                    ),
                    statement_b=Statement(
                        content=str(item["statement_b"]["content"])[:300],
                        source=str(item["statement_b"].get("source", "Unknown"))[:100],
                        year=int(item["statement_b"].get("year", 0)),
                    ),
                    tension_score=round(float(item.get("tension_score", 0.7)), 2),
                    resolution="unresolved",
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return contradictions
