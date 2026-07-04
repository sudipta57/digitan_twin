from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.cognee_service import CogneeService
from backend.services.llm_service import LLMService
from backend.services import figure_store
from backend.services.session import get_user_id

router = APIRouter(prefix="/chat", tags=["chat"])
cognee_svc = CogneeService()
llm_svc = LLMService()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    user_id = get_user_id(http_request)
    if not figure_store.can_access(request.figure_id, user_id):
        raise HTTPException(status_code=403, detail="Access denied for this figure")

    personal_figure = figure_store.get_figure(request.figure_id)

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
            figure_name=personal_figure.name if personal_figure else None,
            relationship=personal_figure.relationship if personal_figure else None,
            bio=personal_figure.description if personal_figure else None,
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
