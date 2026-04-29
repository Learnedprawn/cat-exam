from __future__ import annotations

import re
from dataclasses import dataclass

from cleaner import detect_section_label, normalize_inline_whitespace, normalize_multiline_text


QUESTION_START_INLINE_RE = re.compile(
    r"^(?:q(?:uestion)?\s*)?(\d{1,3})[\)\].:\-]\s+.+",
    re.IGNORECASE,
)
QUESTION_START_STANDALONE_RE = re.compile(
    r"^(?:q(?:uestion)?\s*)?(\d{1,3})[\)\].:\-]$",
    re.IGNORECASE,
)
ANSWER_SECTION_RE = re.compile(r"^(answer\s*key|answers|solutions?)\b", re.IGNORECASE)
ANSWER_ENTRY_RE = re.compile(
    r"(?:(?:q(?:uestion)?\s*)?(\d{1,3})\s*[:.\-]?\s*)([A-D]|-?\d+(?:\.\d+)?(?:\s*/\s*-?\d+(?:\.\d+)?)?)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class QuestionBlock:
    question_number: int
    section: str
    shared_context: str | None
    text: str


@dataclass(slots=True)
class QuestionChunk:
    chunk_id: str
    section_hint: str
    question_number_range: tuple[int, int]
    chunk_text: str


@dataclass(slots=True)
class AnswerChunk:
    chunk_id: str
    chunk_text: str


def split_question_and_answer_regions(text: str) -> tuple[str, str | None]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if ANSWER_SECTION_RE.match(normalize_inline_whitespace(line)):
            question_text = normalize_multiline_text("\n".join(lines[:index]))
            answer_text = normalize_multiline_text("\n".join(lines[index:]))
            return question_text, answer_text or None
    return text, None


def build_question_blocks(text: str) -> list[QuestionBlock]:
    lines = text.splitlines()
    blocks: list[QuestionBlock] = []
    current_section = "VARC"
    current_question_number: int | None = None
    last_question_number = 0
    current_lines: list[str] = []
    active_shared_context: list[str] = []
    pending_shared_context: list[str] = []

    def flush_block() -> None:
        nonlocal current_question_number, current_lines, last_question_number
        if current_question_number is None or not current_lines:
            current_question_number = None
            current_lines = []
            return

        blocks.append(
            QuestionBlock(
                question_number=current_question_number,
                section=current_section,
                shared_context=(
                    normalize_multiline_text("\n".join(active_shared_context))
                    if active_shared_context
                    else None
                ),
                text=normalize_multiline_text("\n".join(current_lines)),
            )
        )
        last_question_number = current_question_number
        current_question_number = None
        current_lines = []

    def match_question_start(line: str) -> int | None:
        for pattern in (QUESTION_START_INLINE_RE, QUESTION_START_STANDALONE_RE):
            match = pattern.match(line)
            if match:
                return int(match.group(1))
        return None

    for raw_line in lines:
        line = normalize_inline_whitespace(raw_line)
        if not line:
            if current_question_number is not None:
                current_lines.append("")
            elif shared_context and shared_context[-1] != "":
                shared_context.append("")
            continue

        section = detect_section_label(line)
        if section:
            flush_block()
            current_section = section
            active_shared_context = []
            pending_shared_context = []
            continue

        question_number = match_question_start(line)
        highest_seen_number = max(last_question_number, current_question_number or 0)
        if question_number is not None and question_number > highest_seen_number:
            flush_block()
            if pending_shared_context:
                active_shared_context = pending_shared_context[:]
                pending_shared_context = []
            current_question_number = question_number
            current_lines = [line]
            continue

        if current_question_number is None:
            pending_shared_context.append(line)
        else:
            current_lines.append(line)

    flush_block()
    return [block for block in blocks if block.text]


def chunk_question_blocks(
    blocks: list[QuestionBlock],
    *,
    max_chunk_chars: int = 6000,
) -> list[QuestionChunk]:
    chunks: list[QuestionChunk] = []
    pending_blocks: list[QuestionBlock] = []
    pending_length = 0

    def flush_chunk() -> None:
        nonlocal pending_blocks, pending_length
        if not pending_blocks:
            return

        start_number = pending_blocks[0].question_number
        end_number = pending_blocks[-1].question_number
        rendered_blocks: list[str] = []
        last_context_key: tuple[str, str | None] | None = None
        for block in pending_blocks:
            context_key = (block.section, block.shared_context)
            parts: list[str] = []
            if context_key != last_context_key:
                parts.append(block.section)
                if block.shared_context:
                    parts.append(block.shared_context)
            parts.append(block.text)
            rendered_blocks.append(normalize_multiline_text("\n".join(parts)))
            last_context_key = context_key
        chunk_text = normalize_multiline_text("\n\n".join(rendered_blocks))
        chunks.append(
            QuestionChunk(
                chunk_id=f"questions_{start_number}_{end_number}",
                section_hint=pending_blocks[0].section,
                question_number_range=(start_number, end_number),
                chunk_text=chunk_text,
            )
        )
        pending_blocks = []
        pending_length = 0

    for block in blocks:
        block_length = len(block.text)
        if pending_blocks and pending_length + block_length > max_chunk_chars:
            flush_chunk()

        pending_blocks.append(block)
        pending_length += block_length

    flush_chunk()
    return chunks


def chunk_answer_text(text: str, *, max_chunk_chars: int = 3000) -> list[AnswerChunk]:
    lines = [normalize_inline_whitespace(line) for line in text.splitlines() if normalize_inline_whitespace(line)]
    chunks: list[AnswerChunk] = []
    pending_lines: list[str] = []
    pending_length = 0
    chunk_index = 1

    for line in lines:
        if pending_lines and pending_length + len(line) > max_chunk_chars:
            chunks.append(
                AnswerChunk(
                    chunk_id=f"answers_{chunk_index}",
                    chunk_text=normalize_multiline_text("\n".join(pending_lines)),
                )
            )
            chunk_index += 1
            pending_lines = []
            pending_length = 0

        pending_lines.append(line)
        pending_length += len(line)

    if pending_lines:
        chunks.append(
            AnswerChunk(
                chunk_id=f"answers_{chunk_index}",
                chunk_text=normalize_multiline_text("\n".join(pending_lines)),
            )
        )

    return chunks


def looks_like_answer_text(text: str) -> bool:
    return bool(ANSWER_ENTRY_RE.search(text))
