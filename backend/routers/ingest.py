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
