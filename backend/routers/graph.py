from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    ContradictionsResponse,
    TopicsResponse,
    ForgetRequest,
    ForgetResponse,
)
from backend.services.cognee_service import CogneeService

router = APIRouter(tags=["graph"])
cognee_svc = CogneeService()

VALID_FIGURES = {"feynman", "tesla", "curie"}

FIGURE_INFO = {
    "feynman": {
        "id": "feynman",
        "name": "Richard Feynman",
        "years": "1918-1988",
        "description": "Theoretical physicist, Nobel laureate, Challenger investigator, eternal teacher.",
        "portrait_url": "/portraits/feynman.jpg",
        "source_count": 5,
    },
    "tesla": {
        "id": "tesla",
        "name": "Nikola Tesla",
        "years": "1856-1943",
        "description": "Inventor of AC power, visionary engineer, dreamer of wireless energy.",
        "portrait_url": "/portraits/tesla.jpg",
        "source_count": 4,
    },
    "curie": {
        "id": "curie",
        "name": "Marie Curie",
        "years": "1867-1934",
        "description": "Pioneer of radioactivity, first woman to win a Nobel Prize, twice.",
        "portrait_url": "/portraits/curie.jpg",
        "source_count": 0,
    },
}


@router.get("/figures")
async def list_figures():
    return {"figures": list(FIGURE_INFO.values())}


@router.get("/figures/{figure_id}")
async def get_figure(figure_id: str):
    if figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")
    return FIGURE_INFO[figure_id]


@router.get("/contradictions/{figure_id}", response_model=ContradictionsResponse)
async def get_contradictions(figure_id: str):
    if figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")

    try:
        contradictions = await cognee_svc.get_contradictions(figure_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ContradictionsResponse(contradictions=contradictions)


@router.get("/topics/{figure_id}", response_model=TopicsResponse)
async def get_topics(figure_id: str):
    if figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")

    try:
        topics = await cognee_svc.get_topics(figure_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return TopicsResponse(topics=topics)


@router.delete("/source", response_model=ForgetResponse)
async def forget_source(request: ForgetRequest):
    if request.figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=404, detail="Figure not found")

    try:
        nodes_removed = await cognee_svc.forget_source(
            figure_id=request.figure_id,
            source_title=request.source_title,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ForgetResponse(status="forgotten", nodes_removed=nodes_removed)
