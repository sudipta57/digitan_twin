import json
import os
import re
from google import genai
from google.genai import types
from backend.models.schemas import Message, Citation


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
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set in environment")
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def generate_response(
        self,
        figure_id: str,
        user_message: str,
        memory_context: str,
        contradiction_context: str,
        conversation_history: list[Message],
    ) -> dict:
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

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        raw_text = response.text
        return self._parse_response(raw_text)

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
        if not recall_results:
            return ""

        parts = []
        if isinstance(recall_results, list):
            for item in recall_results[:8]:
                content = getattr(item, "content", str(item))
                metadata = getattr(item, "metadata", {})
                source = metadata.get("SOURCE_TITLE", "")
                year = metadata.get("YEAR", "")
                if content:
                    parts.append(f"[{source}, {year}]:\n{content[:500]}")
        elif isinstance(recall_results, str):
            parts.append(recall_results)

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
