from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


QuestionType = Literal["mcq", "tita"]
SectionName = Literal["VARC", "DILR", "QA"]


class Option(BaseModel):
    option_id: str
    option_text: str

    @field_validator("option_id")
    @classmethod
    def normalize_option_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("option_text")
    @classmethod
    def normalize_option_text(cls, value: str) -> str:
        return " ".join(value.split())


class ParsedQuestion(BaseModel):
    question_id: str | None = None
    question_number: int
    section: SectionName
    question_type: QuestionType
    question_text: str
    options: list[Option] | None = None
    correct_answer: str | None = None

    @field_validator("question_text")
    @classmethod
    def normalize_question_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("correct_answer")
    @classmethod
    def normalize_correct_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_shape(self) -> "ParsedQuestion":
        if self.question_type == "mcq":
            if not self.options:
                raise ValueError("MCQ questions must have options.")
        elif self.options:
            raise ValueError("TITA questions must not include options.")
        return self


class SkippedItem(BaseModel):
    reason: str
    source_excerpt: str | None = None


class QuestionChunkResult(BaseModel):
    questions: list[ParsedQuestion] = Field(default_factory=list)
    invalid_items: list[SkippedItem] = Field(default_factory=list)


class ParsedAnswer(BaseModel):
    question_number: int
    answer: str

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        return " ".join(value.split())


class AnswerChunkResult(BaseModel):
    answers: list[ParsedAnswer] = Field(default_factory=list)
    invalid_items: list[SkippedItem] = Field(default_factory=list)


class ParsedSet(BaseModel):
    set_id: str | None = None
    section: SectionName
    shared_context: str | None = None
    image_link: str | None = None
    questions: list[ParsedQuestion] = Field(default_factory=list)

    @field_validator("shared_context")
    @classmethod
    def normalize_shared_context(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_set_shape(self) -> "ParsedSet":
        if not self.questions:
            raise ValueError("Sets must include at least one question.")
        if any(question.section != self.section for question in self.questions):
            raise ValueError("All questions in a set must match the set section.")
        return self


class FinalPaper(BaseModel):
    paper_id: str
    year: int
    slot: int
    sets: list[ParsedSet]
