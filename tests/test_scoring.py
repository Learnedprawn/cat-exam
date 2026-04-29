from __future__ import annotations

import unittest

from backend.app.models import Option, Paper, StoredQuestion, StoredSet
from backend.app.scoring import score_submission


class ScoringTests(unittest.TestCase):
    def test_missing_answer_key_is_ungraded_not_incorrect(self) -> None:
        paper = Paper(
            paper_id="2024_slot_1",
            year=2024,
            slot=1,
            sets=[
                StoredSet(
                    set_id="set1",
                    section="VARC",
                    shared_context="Passage",
                    image_link=None,
                    questions=[
                        StoredQuestion(
                            question_id="q1",
                            question_number=1,
                            section="VARC",
                            question_type="mcq",
                            question_text="Choose one",
                            options=[Option(option_id="A", option_text="One")],
                            correct_answer="A",
                        )
                    ],
                ),
                StoredSet(
                    set_id="set2",
                    section="QA",
                    questions=[
                        StoredQuestion(
                            question_id="q2",
                            question_number=2,
                            section="QA",
                            question_type="tita",
                            question_text="Enter value",
                            correct_answer=None,
                        )
                    ],
                ),
            ],
        )

        result = score_submission(paper, {"q1": "A", "q2": "42"})

        self.assertEqual(result.total_questions, 2)
        self.assertEqual(result.gradable_questions, 1)
        self.assertEqual(result.ungraded_questions, 1)
        self.assertEqual(result.attempted, 2)
        self.assertEqual(result.correct, 1)
        self.assertEqual(result.incorrect, 0)
        self.assertEqual(result.score, 1)
        self.assertFalse(result.results[1].is_gradable)
        self.assertFalse(result.results[1].is_correct)

    def test_tita_questions_reject_options(self) -> None:
        with self.assertRaises(ValueError):
            StoredQuestion(
                question_id="q3",
                question_number=3,
                section="QA",
                question_type="tita",
                question_text="Bad tita",
                options=[Option(option_id="A", option_text="Nope")],
                correct_answer=None,
            )


if __name__ == "__main__":
    unittest.main()
