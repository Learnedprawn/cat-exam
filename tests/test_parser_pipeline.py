from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PARSER_ROOT = REPO_ROOT / "parser"
if str(PARSER_ROOT) not in sys.path:
    sys.path.insert(0, str(PARSER_ROOT))

from chunker import build_question_blocks, split_question_and_answer_regions
from cleaner import clean_pages
from main import build_sets, deduplicate_questions, infer_metadata, stable_question_id
from schema import ParsedQuestion


class ParserPipelineTests(unittest.TestCase):
    def test_infer_metadata_from_filename(self) -> None:
        paper_id, year, slot = infer_metadata(
            "/tmp/2024_slot1.pdf",
            paper_id=None,
            year=None,
            slot=None,
        )

        self.assertEqual((paper_id, year, slot), ("2024_slot_1", 2024, 1))

    def test_infer_metadata_requires_overrides_when_filename_missing(self) -> None:
        with self.assertRaises(ValueError):
            infer_metadata("/tmp/mock-paper.pdf", paper_id=None, year=None, slot=None)

    def test_stable_question_id_is_whitespace_insensitive(self) -> None:
        first_id = stable_question_id(7, "What is   2 + 2?")
        second_id = stable_question_id(7, "What is 2 + 2?")

        self.assertEqual(first_id, second_id)

    def test_split_question_and_answer_regions(self) -> None:
        question_text, answer_text = split_question_and_answer_regions(
            "VARC\n1. First question\n2. Second question\nAnswer Key\n1. B\n2. 12"
        )

        self.assertIn("First question", question_text)
        self.assertEqual(answer_text, "Answer Key\n1. B\n2. 12")

    def test_build_question_blocks_tracks_section_and_numbers(self) -> None:
        blocks = build_question_blocks(
            "VARC\nPassage line\n1. First question\nA. x\n2. Second question\n\nQA\n3. Third question"
        )

        self.assertEqual([block.question_number for block in blocks], [1, 2, 3])
        self.assertEqual(blocks[0].section, "VARC")
        self.assertEqual(blocks[0].shared_context, "Passage line")
        self.assertEqual(blocks[1].shared_context, "Passage line")
        self.assertIsNone(blocks[-1].shared_context)
        self.assertEqual(blocks[-1].section, "QA")

    def test_build_question_blocks_handles_standalone_question_numbers(self) -> None:
        blocks = build_question_blocks(
            "\n".join(
                [
                    "SECTION: VERBAL ABILITY AND READING COMPREHENSION",
                    "Directions",
                    "1.",
                    "First question stem",
                    "A. Option one",
                    "2.",
                    "Second question stem",
                ]
            )
        )

        self.assertEqual([block.question_number for block in blocks], [1, 2])
        self.assertIn("First question stem", blocks[0].text)

    def test_build_question_blocks_ignores_numbered_list_items_inside_question(self) -> None:
        blocks = build_question_blocks(
            "\n".join(
                [
                    "VARC",
                    "20.",
                    "Choose the odd sentence.",
                    "1. First sentence",
                    "2. Second sentence",
                    "3. Third sentence",
                    "21.",
                    "Next question stem",
                ]
            )
        )

        self.assertEqual([block.question_number for block in blocks], [20, 21])
        self.assertIn("1. First sentence", blocks[0].text)

    def test_build_question_blocks_detects_di_logical_reasoning_section_alias(self) -> None:
        blocks = build_question_blocks(
            "\n".join(
                [
                    "SECTION: DI & LOGICAL REASONING",
                    "47.",
                    "Question text",
                ]
            )
        )

        self.assertEqual(blocks[0].section, "DILR")

    def test_clean_pages_removes_repeated_headers_and_footers(self) -> None:
        cleaned = clean_pages(
            [
                "CAT 2024\nQuestion 1\nPage 1",
                "CAT 2024\nQuestion 2\nPage 1",
            ]
        )

        self.assertNotIn("CAT 2024", cleaned)
        self.assertIn("Question 1", cleaned)
        self.assertIn("Question 2", cleaned)

    def test_deduplicate_questions_prefers_record_with_answer(self) -> None:
        without_answer = ParsedQuestion(
            question_number=1,
            section="VARC",
            question_type="tita",
            question_text="What is x?",
            correct_answer=None,
        )
        with_answer = ParsedQuestion(
            question_number=1,
            section="VARC",
            question_type="tita",
            question_text="What is x?",
            correct_answer="3",
        )

        deduplicated = deduplicate_questions([without_answer, with_answer])

        self.assertEqual(len(deduplicated), 1)
        self.assertEqual(deduplicated[0].correct_answer, "3")

    def test_build_sets_groups_shared_context_and_keeps_singletons(self) -> None:
        blocks = build_question_blocks(
            "\n".join(
                [
                    "VARC",
                    "Passage one",
                    "1. First question",
                    "A. x",
                    "2. Second question",
                    "QA",
                    "3. Third question",
                ]
            )
        )
        questions = [
            ParsedQuestion(
                question_id="q1",
                question_number=1,
                section="VARC",
                question_type="mcq",
                question_text="First question",
                options=[{"option_id": "A", "option_text": "x"}],
            ),
            ParsedQuestion(
                question_id="q2",
                question_number=2,
                section="VARC",
                question_type="tita",
                question_text="Second question",
            ),
            ParsedQuestion(
                question_id="q3",
                question_number=3,
                section="QA",
                question_type="tita",
                question_text="Third question",
            ),
        ]

        sets = build_sets(questions, blocks)

        self.assertEqual(len(sets), 2)
        self.assertEqual([question.question_number for question in sets[0].questions], [1, 2])
        self.assertEqual(sets[0].shared_context, "Passage one")
        self.assertIsNone(sets[0].image_link)
        self.assertEqual([question.question_number for question in sets[1].questions], [3])
        self.assertIsNone(sets[1].shared_context)


if __name__ == "__main__":
    unittest.main()
