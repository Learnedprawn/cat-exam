from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


QuestionType = Literal["mcq", "tita"]


class Option(BaseModel):
    option_id: str
    option_text: str


class StoredQuestion(BaseModel):
    question_id: str
    question_number: int
    section: str
    question_type: QuestionType
    question_text: str
    options: list[Option] | None = None
    correct_answer: str | None = None

    @model_validator(mode="after")
    def validate_question_shape(self) -> "StoredQuestion":
        if self.question_type == "mcq":
            if not self.options:
                raise ValueError("MCQ questions must include options.")
        elif self.options:
            raise ValueError("TITA questions must not include options.")
        return self


class StoredSet(BaseModel):
    set_id: str
    section: str
    shared_context: str | None = None
    image_link: str | None = None
    questions: list[StoredQuestion]

    @model_validator(mode="after")
    def validate_set_shape(self) -> "StoredSet":
        if not self.questions:
            raise ValueError("Sets must include at least one question.")
        if any(question.section != self.section for question in self.questions):
            raise ValueError("All questions in a set must match the set section.")
        return self


class Paper(BaseModel):
    paper_id: str
    year: int
    slot: int
    sets: list[StoredSet]


class PaperSummary(BaseModel):
    paper_id: str
    year: int
    slot: int


class PublicQuestion(BaseModel):
    question_id: str
    question_number: int
    section: str
    question_type: QuestionType
    question_text: str
    options: list[Option] | None = None

    @model_validator(mode="after")
    def validate_question_shape(self) -> "PublicQuestion":
        if self.question_type == "mcq":
            if not self.options:
                raise ValueError("MCQ questions must include options.")
        elif self.options:
            raise ValueError("TITA questions must not include options.")
        return self


class PublicSet(BaseModel):
    set_id: str
    section: str
    shared_context: str | None = None
    image_link: str | None = None
    questions: list[PublicQuestion]

    @model_validator(mode="after")
    def validate_set_shape(self) -> "PublicSet":
        if not self.questions:
            raise ValueError("Sets must include at least one question.")
        if any(question.section != self.section for question in self.questions):
            raise ValueError("All questions in a set must match the set section.")
        return self


class PublicPaper(BaseModel):
    paper_id: str
    year: int
    slot: int
    sets: list[PublicSet]


class SubmitRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class QuestionResult(BaseModel):
    question_id: str
    question_number: int
    section: str
    submitted_answer: str | None
    is_attempted: bool
    is_gradable: bool
    is_correct: bool


class SubmitResponse(BaseModel):
    total_questions: int
    gradable_questions: int
    ungraded_questions: int
    attempted: int
    correct: int
    incorrect: int
    score: int
    results: list[QuestionResult]
