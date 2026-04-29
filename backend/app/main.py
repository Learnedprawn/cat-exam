from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import PaperSummary, PublicPaper, SubmitRequest, SubmitResponse
from .repository import list_papers, load_paper, to_public_paper
from .scoring import score_submission


def _get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(title="CAT Exam App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/papers", response_model=list[PaperSummary])
def get_papers() -> list[PaperSummary]:
    return list_papers()


@app.get("/api/papers/{paper_id}", response_model=PublicPaper)
def get_paper(paper_id: str) -> PublicPaper:
    paper = load_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return to_public_paper(paper)


@app.post("/api/papers/{paper_id}/submit", response_model=SubmitResponse)
def submit_paper(paper_id: str, payload: SubmitRequest) -> SubmitResponse:
    paper = load_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return score_submission(paper, payload.answers)
