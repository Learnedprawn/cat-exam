export type QuestionType = "mcq" | "tita";

export type Option = {
  option_id: string;
  option_text: string;
};

export type PaperSummary = {
  paper_id: string;
  year: number;
  slot: number;
};

export type Question = {
  question_id: string;
  question_number: number;
  section: string;
  question_type: QuestionType;
  question_text: string;
  options?: Option[];
};

export type QuestionSet = {
  set_id: string;
  section: string;
  shared_context?: string | null;
  image_link?: string | null;
  questions: Question[];
};

export type Paper = {
  paper_id: string;
  year: number;
  slot: number;
  sets: QuestionSet[];
};

export type QuestionResult = {
  question_id: string;
  question_number: number;
  section: string;
  submitted_answer: string | null;
  is_attempted: boolean;
  is_gradable: boolean;
  is_correct: boolean;
};

export type SubmitResponse = {
  total_questions: number;
  gradable_questions: number;
  ungraded_questions: number;
  attempted: number;
  correct: number;
  incorrect: number;
  score: number;
  results: QuestionResult[];
};
