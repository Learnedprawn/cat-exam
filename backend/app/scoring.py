from __future__ import annotations

from .models import Paper, QuestionResult, SubmitResponse


def _is_valid_tita(answer: str) -> bool:
    try:
        float(answer)
    except ValueError:
        return False
    return True


def _iter_questions(paper: Paper):
    for question_set in paper.sets:
        yield from question_set.questions


def score_submission(paper: Paper, answers: dict[str, str]) -> SubmitResponse:
    attempted = 0
    gradable_attempted = 0
    correct = 0
    gradable_questions = 0
    results: list[QuestionResult] = []
    all_questions = list(_iter_questions(paper))

    for question in all_questions:
        submitted_raw = answers.get(question.question_id)
        submitted_answer = submitted_raw.strip() if submitted_raw is not None else None
        is_attempted = bool(submitted_answer)
        is_gradable = question.correct_answer is not None
        is_correct = False

        if is_gradable:
            gradable_questions += 1

        if is_attempted:
            attempted += 1
            if is_gradable and question.question_type == "mcq":
                gradable_attempted += 1
                valid_options = {option.option_id for option in question.options}
                is_correct = (
                    submitted_answer in valid_options
                    and submitted_answer == question.correct_answer
                )
            elif is_gradable:
                gradable_attempted += 1
                is_correct = _is_valid_tita(submitted_answer) and (
                    submitted_answer == question.correct_answer
                )

            if is_correct:
                correct += 1

        results.append(
            QuestionResult(
                question_id=question.question_id,
                question_number=question.question_number,
                section=question.section,
                submitted_answer=submitted_answer,
                is_attempted=is_attempted,
                is_gradable=is_gradable,
                is_correct=is_correct,
            )
        )

    incorrect = gradable_attempted - correct
    return SubmitResponse(
        total_questions=len(all_questions),
        gradable_questions=gradable_questions,
        ungraded_questions=len(all_questions) - gradable_questions,
        attempted=attempted,
        correct=correct,
        incorrect=incorrect,
        score=correct,
        results=results,
    )
