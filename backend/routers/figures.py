from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import CreateFigureRequest, CreateFigureResponse, FiguresResponse
from backend.models.constants import PUBLIC_FIGURES, PUBLIC_FIGURE_IDS
from backend.services import figure_store
from backend.services.session import get_user_id
from backend.services.cognee_service import CogneeService

router = APIRouter(prefix="/figures", tags=["figures"])
cognee_svc = CogneeService()


@router.get("", response_model=FiguresResponse)
async def list_figures(request: Request):
    user_id = get_user_id(request)
    personal = figure_store.list_for_user(user_id) if user_id else []
    return FiguresResponse(public=PUBLIC_FIGURES, personal=personal)


@router.post("", response_model=CreateFigureResponse)
async def create_figure(body: CreateFigureRequest, request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")

    info = figure_store.create_figure(user_id, body)
    slug = info.id[len(user_id) + 1:]
    return CreateFigureResponse(
        figure_id=info.id, slug=slug, dataset_name=f"figure_{info.id}"
    )


@router.delete("/{figure_id}")
async def delete_figure(figure_id: str, request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if figure_id in PUBLIC_FIGURE_IDS or not figure_id.startswith(f"{user_id}_"):
        raise HTTPException(status_code=403, detail="Not your twin")

    figure_store.delete_figure(user_id, figure_id)
    try:
        await cognee_svc.forget_figure(figure_id)
    except Exception:
        pass
    return {"status": "deleted"}
