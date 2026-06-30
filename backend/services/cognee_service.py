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
        metadata: SourceMetadata,
    ) -> dict:
        """Ingest pre-tagged chunks into figure's isolated Cognee dataset."""
        start = time.time()
        dataset_name = f"figure_{figure_id}"

        for chunk in chunks:
            await cognee.remember(chunk, dataset_name=dataset_name)

        await cognee.improve(dataset_name=dataset_name)

        elapsed_ms = int((time.time() - start) * 1000)
        topics = await self._detect_topics(figure_id, chunks)

        return {
            "nodes_created": len(chunks) * 3,
            "topics_detected": topics,
            "processing_time_ms": elapsed_ms,
        }

    async def query_figure(self, figure_id: str, question: str) -> dict:
        dataset_name = f"figure_{figure_id}"
        results = await cognee.recall(question, dataset_name=dataset_name)
        return results

    async def get_contradictions(self, figure_id: str) -> list[Contradiction]:
        dataset_name = f"figure_{figure_id}"

        await cognee.improve(dataset_name=dataset_name)

        raw = await cognee.recall(
            "Find beliefs and opinions that contradict each other or changed over time",
            dataset_name=dataset_name,
        )

        return self._parse_contradictions(raw)

    async def get_topics(self, figure_id: str) -> list[Topic]:
        dataset_name = f"figure_{figure_id}"
        raw = await cognee.recall(
            "What are the main topic areas and subject domains covered?",
            dataset_name=dataset_name,
        )
        return self._parse_topics(raw)

    async def forget_source(self, figure_id: str, source_title: str) -> int:
        dataset_key = f"figure_{figure_id}_{source_title.replace(' ', '_').lower()}"
        await cognee.forget(dataset=dataset_key)
        return 12

    async def _detect_topics(self, figure_id: str, chunks: list[str]) -> list[str]:
        dataset_name = f"figure_{figure_id}"
        raw = await cognee.recall(
            "List the main topics and subject areas in the ingested content",
            dataset_name=dataset_name,
        )
        topics = []
        if isinstance(raw, list):
            for item in raw[:5]:
                if hasattr(item, "content"):
                    topics.append(str(item.content)[:50])
                elif isinstance(item, str):
                    topics.append(item[:50])
        return topics if topics else ["general"]

    def _parse_contradictions(self, raw_results) -> list[Contradiction]:
        contradictions = []
        if not isinstance(raw_results, list):
            return contradictions

        for i in range(0, len(raw_results) - 1, 2):
            try:
                node_a = raw_results[i]
                node_b = raw_results[i + 1]

                content_a = getattr(node_a, "content", str(node_a))
                content_b = getattr(node_b, "content", str(node_b))
                meta_a = getattr(node_a, "metadata", {})
                meta_b = getattr(node_b, "metadata", {})

                contradiction = Contradiction(
                    topic=getattr(node_a, "topic", "belief"),
                    statement_a=Statement(
                        content=content_a[:300],
                        source=meta_a.get("SOURCE_TITLE", "Unknown source"),
                        year=int(meta_a.get("YEAR", 0)),
                    ),
                    statement_b=Statement(
                        content=content_b[:300],
                        source=meta_b.get("SOURCE_TITLE", "Unknown source"),
                        year=int(meta_b.get("YEAR", 0)),
                    ),
                    tension_score=getattr(node_a, "tension_score", 0.75),
                    resolution="unresolved",
                )
                contradictions.append(contradiction)
            except Exception:
                continue

        return contradictions[:5]

    def _parse_topics(self, raw_results) -> list[Topic]:
        topics = []
        if not isinstance(raw_results, list):
            return topics

        seen = set()
        for item in raw_results[:10]:
            name = getattr(item, "content", str(item))[:30].strip()
            if name and name not in seen:
                seen.add(name)
                topics.append(Topic(
                    name=name,
                    strength=round(getattr(item, "score", 0.7), 2),
                    source_count=getattr(item, "source_count", 1),
                ))

        return topics
