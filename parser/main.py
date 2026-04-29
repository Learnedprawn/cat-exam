from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from cleaner import clean_pages, normalize_inline_whitespace
from chunker import (
    QuestionBlock,
    build_question_blocks,
    chunk_answer_text,
    chunk_question_blocks,
    looks_like_answer_text,
    split_question_and_answer_regions,
)
from extract import extract_pages
from llm_parser import LLMParser, merge_answers
from schema import FinalPaper, ParsedAnswer, ParsedQuestion, ParsedSet


DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "backend" / "data" / "papers"
DEFAULT_ERROR_LOG = Path(__file__).resolve().parent / "output" / "parse_errors.jsonl"
FILENAME_RE = re.compile(r"(?P<year>20\d{2})[_\- ]*slot[_\- ]*(?P<slot>\d)", re.IGNORECASE)


class ProgressReporter:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()

    def log(self, message: str) -> None:
        elapsed = time.perf_counter() - self.started_at
        print(f"[{elapsed:6.1f}s] {message}", file=sys.stderr, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse CAT exam PDFs into paper JSON.")
    parser.add_argument("--input", required=True, help="Path to the CAT question PDF.")
    parser.add_argument("--answers", help="Optional separate answer-key PDF or text file.")
    parser.add_argument("--paper-id")
    parser.add_argument("--year", type=int)
    parser.add_argument("--slot", type=int)
    parser.add_argument("--output", help="Explicit output path for the generated JSON.")
    return parser.parse_args()


def infer_metadata(
    input_path: str,
    *,
    paper_id: str | None,
    year: int | None,
    slot: int | None,
) -> tuple[str, int, int]:
    inferred_year = year
    inferred_slot = slot
    match = FILENAME_RE.search(Path(input_path).stem)

    if match:
        inferred_year = inferred_year or int(match.group("year"))
        inferred_slot = inferred_slot or int(match.group("slot"))

    if inferred_year is None or inferred_slot is None:
        raise ValueError("Unable to infer year/slot from filename. Provide --year and --slot.")

    resolved_paper_id = paper_id or f"{inferred_year}_slot_{inferred_slot}"
    return resolved_paper_id, inferred_year, inferred_slot


def stable_question_id(question_number: int, question_text: str) -> str:
    normalized = normalize_inline_whitespace(question_text).lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"q_{question_number}_{digest}"


def stable_set_id(
    first_question_number: int,
    section: str,
    shared_context: str | None,
) -> str:
    normalized = normalize_inline_whitespace(shared_context or section).lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"set_{first_question_number}_{digest}"


def deduplicate_questions(questions: list[ParsedQuestion]) -> list[ParsedQuestion]:
    best_by_text: dict[str, ParsedQuestion] = {}

    for question in questions:
        key = normalize_inline_whitespace(question.question_text).lower()
        existing = best_by_text.get(key)
        if existing is None:
            best_by_text[key] = question
            continue

        existing_score = int(existing.correct_answer is not None) + int(bool(existing.options))
        candidate_score = int(question.correct_answer is not None) + int(bool(question.options))
        if candidate_score > existing_score:
            best_by_text[key] = question

    return sorted(best_by_text.values(), key=lambda item: item.question_number)


def build_sets(
    questions: list[ParsedQuestion],
    blocks: list[QuestionBlock],
) -> list[ParsedSet]:
    metadata_by_number = {
        block.question_number: {
            "section": block.section,
            "shared_context": block.shared_context,
        }
        for block in blocks
    }
    sorted_questions = sorted(questions, key=lambda item: item.question_number)
    sets: list[ParsedSet] = []
    current_questions: list[ParsedQuestion] = []
    current_section: str | None = None
    current_shared_context: str | None = None

    def flush_set() -> None:
        nonlocal current_questions, current_section, current_shared_context
        if not current_questions or current_section is None:
            current_questions = []
            current_section = None
            current_shared_context = None
            return
        first_number = current_questions[0].question_number
        sets.append(
            ParsedSet(
                set_id=stable_set_id(first_number, current_section, current_shared_context),
                section=current_section,
                shared_context=current_shared_context,
                image_link=None,
                questions=current_questions,
            )
        )
        current_questions = []
        current_section = None
        current_shared_context = None

    for question in sorted_questions:
        metadata = metadata_by_number.get(
            question.question_number,
            {"section": question.section, "shared_context": None},
        )
        shared_context = metadata["shared_context"]
        section = metadata["section"]

        same_group = (
            current_questions
            and current_section == section
            and current_shared_context is not None
            and current_shared_context == shared_context
        )
        if not same_group:
            flush_set()
            current_section = section
            current_shared_context = shared_context
        current_questions.append(question.model_copy(update={"section": section}))
        if shared_context is None:
            flush_set()

    flush_set()
    return sets


def build_output_path(output: str | None, paper_id: str) -> Path:
    if output:
        return Path(output)
    return DEFAULT_OUTPUT_ROOT / f"{paper_id}.json"


def is_fatal_parse_error(error: Exception) -> bool:
    message = str(error).lower()
    fatal_markers = (
        "api_key",
        "openai_api_key",
        "authentication",
        "auth",
        "rate limit",
        "connection",
        "timeout",
        "network",
        "permission",
        "quota",
        "billing",
    )
    return any(marker in message for marker in fatal_markers)


def parse_questions(
    parser: LLMParser,
    question_text: str,
    reporter: ProgressReporter,
) -> tuple[list[QuestionBlock], list[ParsedQuestion]]:
    # Keep question-block metadata so grouped sets can be reconstructed after parsing.
    blocks = build_question_blocks(question_text)
    chunks = chunk_question_blocks(blocks)
    questions: list[ParsedQuestion] = []
    failures: list[tuple[str, Exception]] = []
    reporter.log(
        f"Parsing questions from {len(blocks)} detected blocks across {len(chunks)} chunk(s)."
    )

    for index, chunk in enumerate(chunks, start=1):
        reporter.log(
            f"Question chunk {index}/{len(chunks)}: {chunk.chunk_id} "
            f"(questions {chunk.question_number_range[0]}-{chunk.question_number_range[1]})."
        )
        try:
            result = parser.parse_question_chunk(chunk.chunk_id, chunk.chunk_text)
        except Exception as exc:
            failures.append((chunk.chunk_id, exc))
            if is_fatal_parse_error(exc):
                raise RuntimeError(
                    f"Question parsing failed for {chunk.chunk_id}: {exc}"
                ) from exc
            reporter.log(f"Skipped {chunk.chunk_id} after repeated parse failures.")
            continue
        questions.extend(result.questions)
        reporter.log(
            f"Completed {chunk.chunk_id}: extracted {len(result.questions)} question(s)."
        )

    if not questions and failures:
        chunk_id, error = failures[0]
        raise RuntimeError(
            f"Question parsing failed for all {len(failures)} chunks. First failure in {chunk_id}: {error}"
        ) from error

    return blocks, questions


def parse_answers(
    parser: LLMParser,
    answer_text: str | None,
    reporter: ProgressReporter,
) -> list[ParsedAnswer]:
    if not answer_text or not looks_like_answer_text(answer_text):
        reporter.log("No answer-key region detected; skipping answer parsing.")
        return []

    chunks = chunk_answer_text(answer_text)
    reporter.log(f"Parsing answers across {len(chunks)} chunk(s).")
    answers: list[ParsedAnswer] = []
    for index, chunk in enumerate(chunks, start=1):
        reporter.log(f"Answer chunk {index}/{len(chunks)}: {chunk.chunk_id}.")
        try:
            result = parser.parse_answer_chunk(chunk.chunk_id, chunk.chunk_text)
        except Exception as exc:
            if is_fatal_parse_error(exc):
                raise RuntimeError(
                    f"Answer parsing failed for {chunk.chunk_id}: {exc}"
                ) from exc
            reporter.log(f"Skipped {chunk.chunk_id} after repeated parse failures.")
            continue
        answers.extend(result.answers)
        reporter.log(
            f"Completed {chunk.chunk_id}: extracted {len(result.answers)} answer(s)."
        )
    return answers


def run() -> Path:
    args = parse_args()
    reporter = ProgressReporter()
    paper_id, year, slot = infer_metadata(
        args.input,
        paper_id=args.paper_id,
        year=args.year,
        slot=args.slot,
    )
    output_path = build_output_path(args.output, paper_id)
    reporter.log(f"Starting parse for {paper_id} from {args.input}.")
    llm_parser = LLMParser(error_log_path=DEFAULT_ERROR_LOG, progress_callback=reporter.log)

    reporter.log("Extracting question PDF text.")
    question_pages = extract_pages(args.input)
    reporter.log(f"Extracted {len(question_pages)} question page(s); cleaning text.")
    cleaned_question_text = clean_pages(question_pages)
    if not cleaned_question_text.strip():
        raise RuntimeError("PDF extraction produced no text.")

    question_region, embedded_answer_region = split_question_and_answer_regions(cleaned_question_text)
    reporter.log("Running question parser.")
    question_blocks, parsed_questions = parse_questions(llm_parser, question_region, reporter)
    if not parsed_questions:
        raise RuntimeError("No valid questions were parsed.")

    answer_text = embedded_answer_region
    if args.answers:
        reporter.log(f"Extracting answer text from {args.answers}.")
        answer_text = clean_pages(extract_pages(args.answers))

    merged_questions = merge_answers(parsed_questions, parse_answers(llm_parser, answer_text, reporter))
    deduplicated_questions = deduplicate_questions(merged_questions)
    reporter.log(
        f"Merged and deduplicated into {len(deduplicated_questions)} final question(s)."
    )

    final_questions = [
        question.model_copy(
            update={"question_id": stable_question_id(question.question_number, question.question_text)}
        )
        for question in deduplicated_questions
    ]
    final_sets = build_sets(final_questions, question_blocks)
    paper = FinalPaper(
        paper_id=paper_id,
        year=year,
        slot=slot,
        sets=final_sets,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = paper.model_dump(exclude_none=True)
    for question_set in payload["sets"]:
        question_set["image_link"] = None

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    reporter.log(f"Saved parsed paper to {output_path}.")
    return output_path


if __name__ == "__main__":
    saved_path = run()
    print(saved_path)
