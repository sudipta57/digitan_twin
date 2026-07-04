from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import IngestRequest, IngestResponse
from backend.services.parser_service import ParserService
from backend.services.cognee_service import CogneeService
from backend.services import figure_store
from backend.services.session import get_user_id

router = APIRouter(prefix="/ingest", tags=["ingest"])
parser = ParserService()
cognee_svc = CogneeService()


@router.post("", response_model=IngestResponse)
async def ingest_source(request: IngestRequest, http_request: Request):
    user_id = get_user_id(http_request)
    if not figure_store.can_access(request.figure_id, user_id):
        raise HTTPException(status_code=403, detail="Access denied for this figure")

    try:
        chunks = parser.parse(
            source_type=request.source_type,
            content=request.content,
            metadata=request.metadata,
            whatsapp_sender_name=request.whatsapp_sender_name,
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

    figure_store.increment_source_count(request.figure_id)

    return IngestResponse(
        status="success",
        nodes_created=stats["nodes_created"],
        topics_detected=stats["topics_detected"],
        processing_time_ms=stats["processing_time_ms"],
    )
