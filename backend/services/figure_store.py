import re
from backend.models.schemas import FigureInfo, CreateFigureRequest
from backend.models.constants import PUBLIC_FIGURE_IDS

_personal: dict[str, list[FigureInfo]] = {}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def can_access(figure_id: str, user_id: str | None) -> bool:
    """True if figure_id is a public figure, or a personal figure owned by user_id."""
    if figure_id in PUBLIC_FIGURE_IDS:
        return True
    return bool(user_id) and figure_id.startswith(f"{user_id}_")


def list_for_user(user_id: str) -> list[FigureInfo]:
    return _personal.get(user_id, [])


def get_figure(figure_id: str) -> FigureInfo | None:
    for figures in _personal.values():
        for fig in figures:
            if fig.id == figure_id:
                return fig
    return None


def create_figure(user_id: str, body: CreateFigureRequest) -> FigureInfo:
    slug = slugify(body.name)
    figure_id = f"{user_id}_{slug}"
    years = f"{body.years_from}-{body.years_to}" if body.years_to else str(body.years_from)
    info = FigureInfo(
        id=figure_id,
        name=body.name,
        years=years,
        description=body.bio or "",
        is_public=False,
        relationship=body.relationship,
        source_count=0,
    )
    _personal.setdefault(user_id, []).append(info)
    return info


def delete_figure(user_id: str, figure_id: str) -> None:
    if user_id in _personal:
        _personal[user_id] = [f for f in _personal[user_id] if f.id != figure_id]


def increment_source_count(figure_id: str) -> None:
    fig = get_figure(figure_id)
    if fig:
        fig.source_count += 1
