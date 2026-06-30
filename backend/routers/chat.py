from fastapi import APIRouter, HTTPException
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.cognee_service import CogneeService
from backend.services.llm_service import LLMService

router = APIRouter(prefix="/chat", tags=["chat"])
cognee_svc = CogneeService()
llm_svc = LLMService()

VALID_FIGURES = {"feynman", "tesla", "curie"}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.figure_id not in VALID_FIGURES:
        raise HTTPException(status_code=400, detail=f"Unknown figure: {request.figure_id}")

    try:
        recall_results = await cognee_svc.query_figure(
            figure_id=request.figure_id,
            question=request.message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory recall failed: {str(e)}")

    try:
        contradictions = await cognee_svc.get_contradictions(request.figure_id)
    except Exception:
        contradictions = []

    memory_context = llm_svc.format_memory_context(recall_results)
    contradiction_context = llm_svc.format_contradiction_context(contradictions)

    try:
        result = await llm_svc.generate_response(
            figure_id=request.figure_id,
            user_message=request.message,
            memory_context=memory_context,
            contradiction_context=contradiction_context,
            conversation_history=request.conversation_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    return ChatResponse(
        response=result["response"],
        citations=result["citations"],
        sources_used=len(result["citations"]),
        confidence=result["confidence"],
        contradiction_flag=result["contradiction_flag"],
    )
