from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import ContradictionsResponse, TopicsResponse, ForgetRequest, ForgetResponse
from backend.services.cognee_service import CogneeService
from backend.services import figure_store
from backend.services.session import get_user_id

router = APIRouter(tags=["graph"])
cognee_svc = CogneeService()


def _check_access(figure_id: str, request: Request) -> None:
    user_id = get_user_id(request)
    if not figure_store.can_access(figure_id, user_id):
        raise HTTPException(status_code=403, detail="Access denied for this figure")


@router.get("/contradictions/{figure_id}", response_model=ContradictionsResponse)
async def get_contradictions(figure_id: str, request: Request):
    _check_access(figure_id, request)

    try:
        contradictions = await cognee_svc.get_contradictions(figure_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ContradictionsResponse(contradictions=contradictions)


@router.get("/topics/{figure_id}", response_model=TopicsResponse)
async def get_topics(figure_id: str, request: Request):
    _check_access(figure_id, request)

    try:
        topics = await cognee_svc.get_topics(figure_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return TopicsResponse(topics=topics)


@router.delete("/source", response_model=ForgetResponse)
async def forget_source(request: ForgetRequest, http_request: Request):
    _check_access(request.figure_id, http_request)

    try:
        nodes_removed = await cognee_svc.forget_source(
            figure_id=request.figure_id,
            source_title=request.source_title,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ForgetResponse(status="forgotten", nodes_removed=nodes_removed)
