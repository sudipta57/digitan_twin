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

    def parse(self, source_type: str, content: str, metadata: SourceMetadata,
              whatsapp_sender_name: str | None = None) -> list[str]:
        """Entry point. Returns list of tagged text chunks ready for Cognee ingestion."""
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
        tagged_chunks = [self._tag_chunk(chunk, metadata) for chunk in chunks]
        return tagged_chunks

    def _parse_pdf(self, base64_content: str) -> str:
        pdf_bytes = base64.b64decode(base64_content)
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)

    def _parse_url(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        return text

    def _parse_whatsapp(self, content: str, sender_name: str) -> str:
        """Extracts only the messages sent by `sender_name` from a WhatsApp .txt export,
        stripping timestamps and the "sender:" prefix."""
        pattern = re.compile(
            r"^\d{1,2}/\d{1,2}/\d{2,4},\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\s+-\s+(.+?):\s+(.+)$",
            re.IGNORECASE,
        )
        messages = []
        for line in content.split("\n"):
            match = pattern.match(line.strip())
            if not match:
                continue
            sender, message = match.group(1).strip(), match.group(2).strip()
            if sender_name.lower() not in sender.lower():
                continue
            if message in ("<Media omitted>", "This message was deleted"):
                continue
            messages.append(message)
        return "\n".join(messages)

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        return text.strip()

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into ~500 token chunks with 50-token overlap, preferring paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(self.encoder.encode(para))

            if current_tokens + para_tokens > CHUNK_SIZE_TOKENS and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
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
