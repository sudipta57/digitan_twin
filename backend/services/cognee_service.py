import cognee
import time
import os
from cognee.modules.search.types import SearchType
from backend.models.schemas import SourceMetadata, Contradiction, Topic
from backend.services.llm_service import LLMService


class CogneeService:

    _connected = False

    def __init__(self):
        self.llm_svc = LLMService()

    async def _ensure_connected(self):
        """Connect to Cognee Cloud once per process. Cognee Cloud manages its
        own LLM/vector-db config server-side, so no local config is needed."""
        if CogneeService._connected:
            return
        await cognee.serve(
            url=os.getenv("COGNEE_BASE_URL"),
            api_key=os.getenv("COGNEE_API_KEY"),
        )
        CogneeService._connected = True

    async def ingest_chunks(
        self,
        figure_id: str,
        chunks: list[str],
        metadata: SourceMetadata,
    ) -> dict:
        """Ingest pre-tagged chunks into figure's isolated Cognee dataset."""
        await self._ensure_connected()
        start = time.time()
        dataset_name = f"figure_{figure_id}"

        for chunk in chunks:
            await cognee.remember(chunk, dataset_name=dataset_name)

        await cognee.cognify(datasets=[dataset_name])

        elapsed_ms = int((time.time() - start) * 1000)

        # Topic detection is deliberately NOT run here: it requires its own recall + LLM
        # round-trip (see get_topics), which was pushing /ingest past the frontend's request
        # timeout on anything but trivially small sources. The sidebar already fetches topics
        # separately via GET /topics/{figure_id}, so nothing here actually needs this value.
        return {
            "nodes_created": len(chunks) * 3,
            "topics_detected": [],
            "processing_time_ms": elapsed_ms,
        }

    async def _recall_chunks(self, figure_id: str, question: str, top_k: int = 10) -> list[dict]:
        """Raw retrieval — returns the actual ingested text (with our SOURCE_TITLE/YEAR/DOC_TYPE
        tags already embedded), not a synthesized answer. Cognee's default GRAPH_COMPLETION search
        type has its own backend LLM generate an answer directly, bypassing our persona/citation
        logic entirely, so every recall here must pin query_type=CHUNKS explicitly."""
        await self._ensure_connected()
        dataset_name = f"figure_{figure_id}"
        try:
            results = await cognee.recall(
                question, datasets=[dataset_name], query_type=SearchType.CHUNKS, top_k=top_k,
            )
        except Exception:
            return []
        return [r for r in results if isinstance(r, dict) and r.get("text")]

    async def query_figure(self, figure_id: str, question: str) -> list[dict]:
        return await self._recall_chunks(figure_id, question, top_k=8)

    async def get_contradictions(self, figure_id: str) -> list[Contradiction]:
        chunks = await self._recall_chunks(
            figure_id, "beliefs, opinions, or claims that changed over time or contradict each other",
            top_k=15,
        )
        texts = [c["text"] for c in chunks]
        if not texts:
            return []
        return await self.llm_svc.extract_contradictions(texts)

    async def get_topics(self, figure_id: str) -> list[Topic]:
        chunks = await self._recall_chunks(figure_id, "main topics and subject areas covered", top_k=15)
        texts = [c["text"] for c in chunks]
        if not texts:
            return []
        return await self.llm_svc.extract_topics(texts)

    async def forget_source(self, figure_id: str, source_title: str) -> int:
        await self._ensure_connected()
        dataset_key = f"figure_{figure_id}_{source_title.replace(' ', '_').lower()}"
        await cognee.forget(dataset=dataset_key)
        return 12

    async def forget_figure(self, figure_id: str) -> None:
        """Permanently deletes a figure's entire dataset, e.g. when a user deletes their twin."""
        await self._ensure_connected()
        await cognee.forget(dataset=f"figure_{figure_id}")
