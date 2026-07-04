from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pathlib import Path
import logging
import os

# load_dotenv() never overrides a variable already set in the shell, so
# `LLM_PROVIDER=gemini uvicorn backend.main:app ...` takes precedence over .env
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# uvicorn already configured its own loggers by this point (it does so in
# Config.__init__, before importing the "backend.main:app" string), so adding
# our handler here — rather than before load_dotenv — is what makes it land on
# uvicorn's "uvicorn"/"uvicorn.access" loggers too instead of just our own.
# Those two have propagate=False, so a root-only handler would miss them.
_file_handler = logging.FileHandler(Path(__file__).parent / "backend.log")
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.addHandler(_file_handler)

for _uvicorn_logger_name in ("uvicorn", "uvicorn.access"):
    logging.getLogger(_uvicorn_logger_name).addHandler(_file_handler)

from backend.routers import auth, figures, ingest, chat, graph

app = FastAPI(
    title="Dead People's Digital Twin API",
    description="Source-grounded conversations with historical figures via Cognee memory graphs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        os.getenv("FRONTEND_URL", "https://your-app.vercel.app"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(figures.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(graph.router)

app.mount("/portraits", StaticFiles(directory=Path(__file__).parent / "data" / "figures"), name="portraits")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
