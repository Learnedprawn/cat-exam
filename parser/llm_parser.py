from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from schema import AnswerChunkResult, ParsedAnswer, ParsedQuestion, QuestionChunkResult


T = TypeVar("T", bound=BaseModel)


QUESTION_SYSTEM_PROMPT = """You extract CAT exam questions from raw PDF text.
Return only schema-valid structured output.
Do not guess missing question text.
Skip incomplete questions.
Infer section from local chunk context only.
Classify as mcq only when labeled options are present.
Classify as tita when options are absent.
Do not include correct answers in this pass."""

ANSWER_SYSTEM_PROMPT = """You extract CAT exam answer keys from raw text.
Return only schema-valid structured output.
Do not guess missing answers.
Map answers by question number.
Use exact answer text where available."""


class LLMParser:
    def __init__(
        self,
        *,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.1,
        error_log_path: Path | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.error_log_path = error_log_path
        self.progress_callback = progress_callback
        self._client = None

    def parse_question_chunk(self, chunk_id: str, chunk_text: str) -> QuestionChunkResult:
        return self._parse_with_retry(
            chunk_id=chunk_id,
            chunk_text=chunk_text,
            schema=QuestionChunkResult,
            system_prompt=QUESTION_SYSTEM_PROMPT,
        )

    def parse_answer_chunk(self, chunk_id: str, chunk_text: str) -> AnswerChunkResult:
        return self._parse_with_retry(
            chunk_id=chunk_id,
            chunk_text=chunk_text,
            schema=AnswerChunkResult,
            system_prompt=ANSWER_SYSTEM_PROMPT,
        )

    def _parse_with_retry(
        self,
        *,
        chunk_id: str,
        chunk_text: str,
        schema: type[T],
        system_prompt: str,
    ) -> T:
        attempts = 2
        last_error: Exception | None = None
        validation_feedback = ""

        for attempt in range(1, attempts + 1):
            try:
                self._emit_progress(
                    f"{chunk_id}: starting model call (attempt {attempt}/{attempts})"
                )
                return self._call_model(
                    schema=schema,
                    system_prompt=system_prompt,
                    user_text=chunk_text,
                    validation_feedback=validation_feedback,
                )
            except Exception as exc:  # pragma: no cover - network path
                last_error = exc
                self._emit_progress(
                    f"{chunk_id}: attempt {attempt}/{attempts} failed: {exc}"
                )
                validation_feedback = f"Previous attempt failed with: {exc}"

        assert last_error is not None
        self._log_error(chunk_id=chunk_id, chunk_text=chunk_text, error=last_error)
        raise last_error

    def _call_model(
        self,
        *,
        schema: type[T],
        system_prompt: str,
        user_text: str,
        validation_feedback: str,
    ) -> T:
        client = self._get_client()
        messages = [{"role": "system", "content": system_prompt}]
        if validation_feedback:
            messages.append({"role": "system", "content": validation_feedback})
        messages.append({"role": "user", "content": user_text})

        response = client.responses.parse(
            model=self.model,
            temperature=self.temperature,
            input=messages,
            text_format=schema,
        )
        parsed = getattr(response, "output_parsed", None)

        if parsed is not None:
            return parsed

        output_text = getattr(response, "output_text", "")
        if not output_text:
            raise ValueError("Model returned no structured output.")

        try:
            return schema.model_validate_json(output_text)
        except ValidationError as exc:
            raise ValueError(exc.errors()) from exc

    def _get_client(self):  # pragma: no cover - network path
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Export it before running the parser."
                )
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "OpenAI SDK is required for LLM parsing. Install parser dependencies first."
                ) from exc
            self._client = OpenAI(api_key=api_key)
        return self._client

    def _log_error(self, *, chunk_id: str, chunk_text: str, error: Exception) -> None:
        if self.error_log_path is None:
            return

        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunk_id": chunk_id,
            "error": str(error),
            "chunk_text": chunk_text,
        }
        with self.error_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _emit_progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)


def merge_answers(
    questions: list[ParsedQuestion],
    answers: list[ParsedAnswer],
) -> list[ParsedQuestion]:
    answers_by_number = {answer.question_number: answer.answer for answer in answers}
    merged_questions: list[ParsedQuestion] = []

    for question in questions:
        merged_questions.append(
            question.model_copy(
                update={"correct_answer": answers_by_number.get(question.question_number)}
            )
        )

    return merged_questions
