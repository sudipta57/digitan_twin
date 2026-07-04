from backend.models.schemas import FigureInfo

PUBLIC_FIGURES: list[FigureInfo] = [
    FigureInfo(
        id="feynman", name="Richard Feynman", years="1918-1988",
        description="Theoretical physicist, Nobel laureate, Challenger investigator, eternal teacher.",
        portrait_url="/portraits/feynman/portrait.svg", is_public=True, source_count=5,
    ),
    FigureInfo(
        id="tesla", name="Nikola Tesla", years="1856-1943",
        description="Inventor of AC power, visionary engineer, dreamer of wireless energy.",
        portrait_url="/portraits/tesla/portrait.svg", is_public=True, source_count=4,
    ),
    FigureInfo(
        id="curie", name="Marie Curie", years="1867-1934",
        description="Pioneer of radioactivity, first woman to win a Nobel Prize, twice.",
        portrait_url="/portraits/curie/portrait.svg", is_public=True, source_count=0,
    ),
]

PUBLIC_FIGURE_IDS: set[str] = {fig.id for fig in PUBLIC_FIGURES}
