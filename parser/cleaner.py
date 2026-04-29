from __future__ import annotations

import re
from collections import Counter


SECTION_ALIASES = {
    "verbal ability and reading comprehension": "VARC",
    "varc": "VARC",
    "data interpretation and logical reasoning": "DILR",
    "logical reasoning and data interpretation": "DILR",
    "di & logical reasoning": "DILR",
    "di and logical reasoning": "DILR",
    "dilr": "DILR",
    "quantitative ability": "QA",
    "qa": "QA",
}


def normalize_inline_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_multiline_text(text: str) -> str:
    normalized_lines = [normalize_inline_whitespace(line) for line in text.splitlines()]
    compact_lines: list[str] = []
    blank_pending = False

    for line in normalized_lines:
        if not line:
            if compact_lines and not blank_pending:
                compact_lines.append("")
                blank_pending = True
            continue

        compact_lines.append(line)
        blank_pending = False

    while compact_lines and compact_lines[-1] == "":
        compact_lines.pop()

    return "\n".join(compact_lines)


def detect_section_label(line: str) -> str | None:
    lowered = normalize_inline_whitespace(line).lower()
    lowered = re.sub(r"^(section|part)\s*[:\-]?\s*", "", lowered)
    return SECTION_ALIASES.get(lowered)


def _repeated_edge_lines(pages: list[str], from_top: bool) -> set[str]:
    candidates: list[str] = []

    for page in pages:
        lines = [normalize_inline_whitespace(line) for line in page.splitlines()]
        lines = [line for line in lines if line]
        edge_lines = lines[:2] if from_top else lines[-2:]
        candidates.extend(edge_lines)

    counts = Counter(candidates)
    minimum_repeats = max(2, len(pages) // 2)
    return {
        line
        for line, count in counts.items()
        if count >= minimum_repeats and len(line) > 2
    }


def clean_pages(pages: list[str]) -> str:
    if not pages:
        return ""

    repeated_headers = _repeated_edge_lines(pages, from_top=True)
    repeated_footers = _repeated_edge_lines(pages, from_top=False)
    cleaned_pages: list[str] = []

    for page in pages:
        lines = [normalize_inline_whitespace(line) for line in page.splitlines()]
        filtered_lines = [
            line
            for line in lines
            if line and line not in repeated_headers and line not in repeated_footers
        ]
        cleaned_pages.append("\n".join(filtered_lines))

    return normalize_multiline_text("\n\n".join(cleaned_pages))
