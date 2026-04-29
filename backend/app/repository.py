from __future__ import annotations

import json
from pathlib import Path

from .models import Paper, PaperSummary, PublicPaper, PublicQuestion, PublicSet


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "papers"


def load_paper(paper_id: str) -> Paper | None:
    paper_path = DATA_DIR / f"{paper_id}.json"
    if not paper_path.exists():
        return None

    with paper_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return Paper.model_validate(payload)


def list_papers() -> list[PaperSummary]:
    papers: list[PaperSummary] = []
    if not DATA_DIR.exists():
        return papers

    for paper_path in sorted(DATA_DIR.glob("*.json")):
        with paper_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        paper = Paper.model_validate(payload)
        papers.append(
            PaperSummary(paper_id=paper.paper_id, year=paper.year, slot=paper.slot)
        )

    return papers


def to_public_paper(paper: Paper) -> PublicPaper:
    return PublicPaper(
        paper_id=paper.paper_id,
        year=paper.year,
        slot=paper.slot,
        sets=[
            PublicSet(
                set_id=question_set.set_id,
                section=question_set.section,
                shared_context=question_set.shared_context,
                image_link=question_set.image_link,
                questions=[
                    PublicQuestion(
                        question_id=question.question_id,
                        question_number=question.question_number,
                        section=question.section,
                        question_type=question.question_type,
                        question_text=question.question_text,
                        options=question.options,
                    )
                    for question in question_set.questions
                ],
            )
            for question_set in paper.sets
        ],
    )
