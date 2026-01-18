from __future__ import annotations
from pathlib import Path
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from app.embedder import E5Embedder
from app.retriever import RetrieverConfig, SceneRetriever

BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "data" / "artifacts"
STATIC_DIR = BASE_DIR / "static"
MOVIE_DIR = BASE_DIR / "data" / "movie"

app = FastAPI(title="Movie Scene Search Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever: SceneRetriever | None = None


class SearchReq(BaseModel):
    query: str = Field(..., description="사용자 검색 문장")
    top_k: int = Field(5, ge=1, le=5)


class SearchResp(BaseModel):
    results: List[dict]


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.on_event("startup")
def startup() -> None:
    global retriever

    # retriever 로드
    embedder = E5Embedder(model_id="intfloat/multilingual-e5-large")
    cfg = RetrieverConfig(artifacts_dir=ARTIFACTS_DIR)
    retriever = SceneRetriever(embedder=embedder, cfg=cfg)

    # static 서빙
    if not STATIC_DIR.exists():
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # 원본 mp4 서빙
    if not MOVIE_DIR.exists():
        raise FileNotFoundError(f"Movie directory not found: {MOVIE_DIR}")
    app.mount("/media", StaticFiles(directory=str(MOVIE_DIR)), name="media")


@app.post("/search", response_model=SearchResp)
def search(req: SearchReq):
    if retriever is None:
        return {"results": []}
    return {"results": retriever.search(req.query, top_k=req.top_k)}
